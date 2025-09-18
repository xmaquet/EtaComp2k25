#!/usr/bin/env python3
"""
Tests unitaires pour le moteur de règles de tolérances.

Teste les fonctionnalités principales selon les spécifications :
- match unique (normale/grande avec course ; faible/limitée sans course)
- aucun match ⇒ indéterminé
- chevauchement ⇒ lève erreur de validation
- comparaisons graduation avec tolérance EPS
"""

import pytest
import tempfile
from pathlib import Path

from src.etacomp.rules.tolerances import (
    ToleranceRuleEngine, ToleranceRule, Verdict, ConfigurationOverlapError,
    grad_eq, EPS
)
from src.etacomp.models.comparator import ComparatorProfile, RangeType


class TestToleranceRuleEngine:
    """Tests du moteur de règles de tolérances."""
    
    def setup_method(self):
        """Configuration avant chaque test."""
        self.engine = ToleranceRuleEngine()
        
        # Règles de test selon les spécifications
        self.engine.rules["normale"] = [
            ToleranceRule(
                graduation=0.01, course_min=0.0, course_max=10.0,
                Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
            ),
            ToleranceRule(
                graduation=0.01, course_min=10.0, course_max=20.0,
                Emt=0.015, Eml=0.012, Ef=0.003, Eh=0.012
            )
        ]
        
        self.engine.rules["grande"] = [
            ToleranceRule(
                graduation=0.01, course_min=20.0, course_max=30.0,
                Emt=0.025, Eml=0.020, Ef=0.005, Eh=0.020
            )
        ]
        
        self.engine.rules["faible"] = [
            ToleranceRule(
                graduation=0.001,
                Emt=0.008, Eml=0.006, Ef=0.002, Eh=0.006
            )
        ]
        
        self.engine.rules["limitee"] = [
            ToleranceRule(
                graduation=0.001,
                Emt=0.005, Eml=0.004, Ef=0.0015, Eh=0.004
            )
        ]
    
    def test_match_normale_with_course(self):
        """Test match pour famille normale avec course."""
        # Test graduation exacte dans plage
        rule = self.engine.match("normale", 0.01, 5.0)
        assert rule is not None
        assert rule.graduation == 0.01
        assert rule.course_min == 0.0
        assert rule.course_max == 10.0
        
        # Test graduation exacte à la limite
        rule = self.engine.match("normale", 0.01, 10.0)
        assert rule is not None
        assert rule.course_max == 10.0
        
        # Test graduation exacte dans deuxième plage
        rule = self.engine.match("normale", 0.01, 15.0)
        assert rule is not None
        assert rule.course_min == 10.0
        assert rule.course_max == 20.0
    
    def test_match_grande_with_course(self):
        """Test match pour famille grande avec course."""
        rule = self.engine.match("grande", 0.01, 25.0)
        assert rule is not None
        assert rule.graduation == 0.01
        assert rule.course_min == 20.0
        assert rule.course_max == 30.0
    
    def test_match_faible_without_course(self):
        """Test match pour famille faible sans course."""
        rule = self.engine.match("faible", 0.001, None)
        assert rule is not None
        assert rule.graduation == 0.001
        assert rule.course_min is None
        assert rule.course_max is None
        
        # Course ignorée pour faible
        rule = self.engine.match("faible", 0.001, 999.0)
        assert rule is not None
    
    def test_match_limitee_without_course(self):
        """Test match pour famille limitée sans course."""
        rule = self.engine.match("limitee", 0.001, None)
        assert rule is not None
        assert rule.graduation == 0.001
        assert rule.course_min is None
        assert rule.course_max is None
    
    def test_no_match_returns_none(self):
        """Test qu'aucun match retourne None."""
        # Graduation non trouvée
        rule = self.engine.match("normale", 0.005, 5.0)
        assert rule is None
        
        # Course hors plage
        rule = self.engine.match("normale", 0.01, 25.0)
        assert rule is None
        
        # Famille inexistante
        rule = self.engine.match("inexistante", 0.01, 5.0)
        assert rule is None
    
    def test_graduation_tolerance(self):
        """Test tolérance pour les comparaisons de graduation."""
        # Test avec tolérance EPS
        rule = self.engine.match("normale", 0.01 + EPS/2, 5.0)
        assert rule is not None
        
        # Test juste au-delà de la tolérance
        rule = self.engine.match("normale", 0.01 + EPS * 2, 5.0)
        assert rule is None
    
    def test_overlap_detection(self):
        """Test détection de chevauchement."""
        # Créer des règles qui se chevauchent
        overlapping_engine = ToleranceRuleEngine()
        overlapping_engine.rules["normale"] = [
            ToleranceRule(
                graduation=0.01, course_min=0.0, course_max=15.0,
                Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
            ),
            ToleranceRule(
                graduation=0.01, course_min=10.0, course_max=20.0,
                Emt=0.015, Eml=0.012, Ef=0.003, Eh=0.012
            )
        ]
        
        errors = overlapping_engine.validate()
        assert len(errors) > 0
        assert any("chevauchement" in error for error in errors)
    
    def test_duplicate_graduation_faible(self):
        """Test détection de graduation dupliquée pour faible/limitée."""
        duplicate_engine = ToleranceRuleEngine()
        duplicate_engine.rules["faible"] = [
            ToleranceRule(graduation=0.001, Emt=0.008, Eml=0.006, Ef=0.002, Eh=0.006),
            ToleranceRule(graduation=0.001, Emt=0.010, Eml=0.008, Ef=0.003, Eh=0.008)
        ]
        
        errors = duplicate_engine.validate()
        assert len(errors) > 0
        assert any("dupliquée" in error for error in errors)
    
    def test_evaluate_apte(self):
        """Test évaluation avec verdict apte."""
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.01,
            course=5.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        errors = {"Emt": 0.010, "Eml": 0.008, "Ef": 0.002, "Eh": 0.008}
        verdict = self.engine.evaluate(profile, errors)
        
        assert verdict.status == "apte"
        assert verdict.rule is not None
        assert verdict.exceed is None
        assert len(verdict.messages) == 0
    
    def test_evaluate_inapte(self):
        """Test évaluation avec verdict inapte."""
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.01,
            course=5.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        errors = {"Emt": 0.020, "Eml": 0.015, "Ef": 0.005, "Eh": 0.015}
        verdict = self.engine.evaluate(profile, errors)
        
        assert verdict.status == "inapte"
        assert verdict.rule is not None
        assert verdict.exceed is not None
        assert len(verdict.messages) > 0
        assert any("dépasse" in msg for msg in verdict.messages)
    
    def test_evaluate_indetermine_no_rule(self):
        """Test évaluation avec verdict indéterminé (aucune règle)."""
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.005,  # Graduation non couverte
            course=5.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        errors = {"Emt": 0.010, "Eml": 0.008, "Ef": 0.002, "Eh": 0.008}
        verdict = self.engine.evaluate(profile, errors)
        
        assert verdict.status == "indetermine"
        assert verdict.rule is None
        assert len(verdict.messages) > 0
        assert any("Aucune règle" in msg for msg in verdict.messages)
    
    def test_evaluate_indetermine_overlap(self):
        """Test évaluation avec verdict indéterminé (chevauchement)."""
        # Créer un moteur avec chevauchement
        overlap_engine = ToleranceRuleEngine()
        overlap_engine.rules["normale"] = [
            ToleranceRule(
                graduation=0.01, course_min=0.0, course_max=15.0,
                Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
            ),
            ToleranceRule(
                graduation=0.01, course_min=10.0, course_max=20.0,
                Emt=0.015, Eml=0.012, Ef=0.003, Eh=0.012
            )
        ]
        
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.01,
            course=12.0,  # Dans la zone de chevauchement
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        errors = {"Emt": 0.010, "Eml": 0.008, "Ef": 0.002, "Eh": 0.008}
        
        with pytest.raises(ConfigurationOverlapError):
            overlap_engine.match("normale", 0.01, 12.0)
    
    def test_save_load_roundtrip(self):
        """Test sauvegarde et chargement."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Sauvegarder
            self.engine.save(temp_path)
            assert temp_path.exists()
            
            # Charger dans un nouveau moteur
            new_engine = ToleranceRuleEngine()
            new_engine.load(temp_path)
            
            # Vérifier que les règles sont identiques
            assert new_engine.rules == self.engine.rules
            
        finally:
            temp_path.unlink(missing_ok=True)


class TestToleranceRule:
    """Tests de la classe ToleranceRule."""
    
    def test_rule_validation(self):
        """Test validation d'une règle."""
        # Règle valide
        rule = ToleranceRule(
            graduation=0.01, course_min=0.0, course_max=10.0,
            Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
        )
        assert rule.graduation == 0.01
        assert rule.course_min == 0.0
        assert rule.course_max == 10.0
    
    def test_rule_validation_negative_graduation(self):
        """Test validation avec graduation négative."""
        with pytest.raises(ValueError, match="graduation doit être > 0"):
            ToleranceRule(graduation=-0.01, Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010)
    
    def test_rule_validation_course_min_max(self):
        """Test validation des bornes de course."""
        with pytest.raises(ValueError, match="course_min.*course_max"):
            ToleranceRule(
                graduation=0.01, course_min=10.0, course_max=5.0,
                Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
            )
    
    def test_rule_validation_negative_tolerance(self):
        """Test validation avec tolérance négative."""
        with pytest.raises(ValueError, match="Emt doit être >= 0"):
            ToleranceRule(
                graduation=0.01, course_min=0.0, course_max=10.0,
                Emt=-0.013, Eml=0.010, Ef=0.003, Eh=0.010
            )
    
    def test_rule_matches(self):
        """Test méthode matches."""
        rule = ToleranceRule(
            graduation=0.01, course_min=0.0, course_max=10.0,
            Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
        )
        
        # Match exact
        assert rule.matches(0.01, 5.0)
        
        # Match avec tolérance
        assert rule.matches(0.01 + EPS/2, 5.0)
        
        # Pas de match (graduation différente)
        assert not rule.matches(0.005, 5.0)
        
        # Pas de match (course hors plage)
        assert not rule.matches(0.01, 15.0)
    
    def test_rule_matches_faible(self):
        """Test méthode matches pour famille faible."""
        rule = ToleranceRule(graduation=0.001, Emt=0.008, Eml=0.006, Ef=0.002, Eh=0.006)
        
        # Match avec graduation exacte
        assert rule.matches(0.001, None)
        assert rule.matches(0.001, 999.0)  # Course ignorée
        
        # Pas de match
        assert not rule.matches(0.01, None)


class TestGradEq:
    """Tests de la fonction grad_eq."""
    
    def test_grad_eq_exact(self):
        """Test comparaison exacte."""
        assert grad_eq(0.01, 0.01)
        assert grad_eq(0.0, 0.0)
    
    def test_grad_eq_tolerance(self):
        """Test comparaison avec tolérance."""
        assert grad_eq(0.01, 0.01 + EPS/2)
        assert grad_eq(0.01, 0.01 - EPS/2)
        assert not grad_eq(0.01, 0.01 + EPS * 2)
        assert not grad_eq(0.01, 0.01 - EPS * 2)
    
    def test_grad_eq_edge_cases(self):
        """Test cas limites."""
        assert grad_eq(0.0, EPS/2)
        assert grad_eq(0.0, -EPS/2)
        assert not grad_eq(0.0, EPS * 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
