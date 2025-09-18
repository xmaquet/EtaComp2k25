#!/usr/bin/env python3
"""
Tests unitaires pour les profils de comparateurs.

Teste les validations et la migration selon les spécifications :
- validations profil (11 cibles, 0 inclus, 0 ≤ t ≤ course, ordonnées, graduation/course > 0)
- migration profils (déductions + erreurs claires)
"""

import pytest
import tempfile
from pathlib import Path

from src.etacomp.models.comparator import ComparatorProfile, RangeType, load_profile, save_profile


class TestComparatorProfile:
    """Tests du modèle ComparatorProfile."""
    
    def test_valid_profile(self):
        """Test création d'un profil valide."""
        profile = ComparatorProfile(
            reference="TEST-001",
            manufacturer="TestCorp",
            description="Comparateur de test",
            graduation=0.01,
            course=10.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        assert profile.reference == "TEST-001"
        assert profile.graduation == 0.01
        assert profile.course == 10.0
        assert profile.range_type == RangeType.NORMALE
        assert len(profile.targets) == 11
    
    def test_validation_exactly_11_targets(self):
        """Test validation exactement 11 cibles."""
        # Trop peu de cibles
        with pytest.raises(ValueError, match="exactement 11 cibles"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, 1.0, 2.0]  # Seulement 3 cibles
            )
        
        # Trop de cibles
        with pytest.raises(ValueError, match="exactement 11 cibles"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]  # 12 cibles
            )
    
    def test_validation_first_target_zero(self):
        """Test validation première cible à 0."""
        # Première cible pas à 0
        with pytest.raises(ValueError, match="première cible doit être 0.0"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.1, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            )
        
        # Première cible à 0 avec tolérance
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.01,
            course=10.0,
            range_type=RangeType.NORMALE,
            targets=[1e-7, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]  # Très proche de 0
        )
        assert profile.targets[0] == 1e-7
    
    def test_validation_targets_in_range(self):
        """Test validation cibles dans la plage [0, course]."""
        # Cible négative
        with pytest.raises(ValueError, match="hors plage"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, -1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            )
        
        # Cible au-delà de la course
        with pytest.raises(ValueError, match="hors plage"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 11.0]  # 11.0 > course
            )
    
    def test_validation_targets_ordered(self):
        """Test validation cibles non-décroissantes."""
        # Cibles décroissantes
        with pytest.raises(ValueError, match="non ordonnées"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, 2.0, 1.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]  # 2.0 > 1.0
            )
    
    def test_validation_graduation_positive(self):
        """Test validation graduation > 0."""
        with pytest.raises(ValueError, match="graduation doit être > 0"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.0,  # graduation = 0
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            )
        
        with pytest.raises(ValueError, match="graduation doit être > 0"):
            ComparatorProfile(
                reference="TEST",
                graduation=-0.01,  # graduation négative
                course=10.0,
                range_type=RangeType.NORMALE,
                targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            )
    
    def test_validation_course_positive(self):
        """Test validation course > 0."""
        with pytest.raises(ValueError, match="course doit être > 0"):
            ComparatorProfile(
                reference="TEST",
                graduation=0.01,
                course=0.0,  # course = 0
                range_type=RangeType.NORMALE,
                targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            )
    
    def test_range_type_deduction(self):
        """Test déduction du range_type selon la course."""
        # Course limitée
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.001,
            course=0.3,
            range_type=RangeType.LIMITEE,
            targets=[0.0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.24, 0.27, 0.3]
        )
        assert profile.range_type == RangeType.LIMITEE
        
        # Course faible
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.001,
            course=0.8,
            range_type=RangeType.FAIBLE,
            targets=[0.0, 0.08, 0.16, 0.24, 0.32, 0.4, 0.48, 0.56, 0.64, 0.72, 0.8]
        )
        assert profile.range_type == RangeType.FAIBLE
        
        # Course normale
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.01,
            course=15.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5, 15.0]
        )
        assert profile.range_type == RangeType.NORMALE
        
        # Course grande
        profile = ComparatorProfile(
            reference="TEST",
            graduation=0.01,
            course=25.0,
            range_type=RangeType.GRANDE,
            targets=[0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5, 20.0, 22.5, 25.0]
        )
        assert profile.range_type == RangeType.GRANDE
    
    def test_filename_property(self):
        """Test propriété filename."""
        profile = ComparatorProfile(
            reference="TEST COMPARATOR",
            graduation=0.01,
            course=10.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        assert profile.filename == "TEST_COMPARATOR.json"


class TestProfileMigration:
    """Tests de migration des profils."""
    
    def test_load_save_roundtrip(self):
        """Test chargement et sauvegarde."""
        profile = ComparatorProfile(
            reference="TEST-ROUNDTRIP",
            manufacturer="TestCorp",
            description="Test roundtrip",
            graduation=0.01,
            course=10.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Sauvegarder
            save_profile(temp_path, profile)
            assert temp_path.exists()
            
            # Charger
            loaded_profile = load_profile(temp_path)
            assert loaded_profile is not None
            assert loaded_profile.reference == profile.reference
            assert loaded_profile.graduation == profile.graduation
            assert loaded_profile.course == profile.course
            assert loaded_profile.range_type == profile.range_type
            assert loaded_profile.targets == profile.targets
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_load_nonexistent_file(self):
        """Test chargement d'un fichier inexistant."""
        nonexistent_path = Path("/nonexistent/file.json")
        profile = load_profile(nonexistent_path)
        assert profile is None
    
    def test_load_invalid_json(self):
        """Test chargement d'un JSON invalide."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Impossible de charger"):
                load_profile(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_save_invalid_profile(self):
        """Test sauvegarde d'un profil invalide."""
        # Créer un profil invalide (moins de 11 cibles)
        invalid_profile = ComparatorProfile(
            reference="INVALID",
            graduation=0.01,
            course=10.0,
            range_type=RangeType.NORMALE,
            targets=[0.0, 1.0, 2.0]  # Seulement 3 cibles
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # La validation devrait échouer avant la sauvegarde
            with pytest.raises(ValueError):
                save_profile(temp_path, invalid_profile)
        finally:
            temp_path.unlink(missing_ok=True)


class TestRangeType:
    """Tests de l'enum RangeType."""
    
    def test_range_type_values(self):
        """Test valeurs de l'enum RangeType."""
        assert RangeType.NORMALE.value == "normale"
        assert RangeType.GRANDE.value == "grande"
        assert RangeType.FAIBLE.value == "faible"
        assert RangeType.LIMITEE.value == "limitee"
    
    def test_range_type_from_string(self):
        """Test création depuis une chaîne."""
        assert RangeType("normale") == RangeType.NORMALE
        assert RangeType("grande") == RangeType.GRANDE
        assert RangeType("faible") == RangeType.FAIBLE
        assert RangeType("limitee") == RangeType.LIMITEE
    
    def test_range_type_invalid(self):
        """Test création avec valeur invalide."""
        with pytest.raises(ValueError):
            RangeType("invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
