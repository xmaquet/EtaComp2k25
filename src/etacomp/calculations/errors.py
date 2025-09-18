from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from ..models.comparator import ComparatorProfile
from ..models.session import MeasureSeries


@dataclass
class ErrorResults:
    """Résultats des calculs d'erreurs."""
    Emt: float  # Erreur de mesure totale (mm)
    Eml: float  # Erreur de mesure locale (mm)
    Ef: float   # Erreur de fidélité (mm)
    Eh: float   # Erreur d'hystérésis (mm)
    
    # Données détaillées pour diagnostic
    linearity_error: float  # Erreur de linéarité (mm)
    repeatability_error: float  # Erreur de répétabilité (mm)
    hysteresis_error: float  # Erreur d'hystérésis calculée (mm)
    
    # Statistiques par cible
    target_stats: List[Dict[str, float]]  # Stats pour chaque cible
    
    def to_dict(self) -> Dict[str, float]:
        """Convertit en dictionnaire pour l'évaluation des tolérances."""
        return {
            "Emt": self.Emt,
            "Eml": self.Eml,
            "Ef": self.Ef,
            "Eh": self.Eh
        }


class ErrorCalculator:
    """Calculateur d'erreurs selon les normes de métrologie."""
    
    def __init__(self):
        self.tolerance = 1e-6  # Tolérance pour les comparaisons flottantes
    
    def calculate_errors(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> ErrorResults:
        """
        Calcule les erreurs principales selon les spécifications.
        
        Args:
            profile: Profil du comparateur
            series: Liste des séries de mesures (montante/descendante)
        
        Returns:
            ErrorResults avec toutes les erreurs calculées
        """
        if not series:
            raise ValueError("Aucune série de mesures fournie")
        
        # Séparer les séries montantes et descendantes
        ascending_series = [s for s in series if s.direction == "ascending"]
        descending_series = [s for s in series if s.direction == "descending"]
        
        if not ascending_series or not descending_series:
            raise ValueError("Séries montantes et descendantes requises")
        
        # Calculer les erreurs individuelles
        linearity_error = self._calculate_linearity_error(profile, series)
        repeatability_error = self._calculate_repeatability_error(profile, series)
        hysteresis_error = self._calculate_hysteresis_error(profile, ascending_series, descending_series)
        
        # Calculer les erreurs principales selon les normes
        Emt = self._calculate_Emt(profile, series)
        Eml = self._calculate_Eml(profile, series)
        Ef = self._calculate_Ef(profile, series)
        Eh = self._calculate_Eh(profile, ascending_series, descending_series)
        
        # Statistiques par cible
        target_stats = self._calculate_target_stats(profile, series)
        
        return ErrorResults(
            Emt=Emt,
            Eml=Eml,
            Ef=Ef,
            Eh=Eh,
            linearity_error=linearity_error,
            repeatability_error=repeatability_error,
            hysteresis_error=hysteresis_error,
            target_stats=target_stats
        )
    
    def _calculate_linearity_error(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> float:
        """Calcule l'erreur de linéarité."""
        # Pour chaque cible, calculer l'écart moyen par rapport à la valeur théorique
        errors = []
        
        for target_idx, target_value in enumerate(profile.targets):
            target_errors = []
            
            for series_data in series:
                if target_idx < len(series_data.measurements):
                    measured = series_data.measurements[target_idx]
                    error = abs(measured - target_value)
                    target_errors.append(error)
            
            if target_errors:
                avg_error = sum(target_errors) / len(target_errors)
                errors.append(avg_error)
        
        return max(errors) if errors else 0.0
    
    def _calculate_repeatability_error(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> float:
        """Calcule l'erreur de répétabilité."""
        # Calculer l'écart-type des mesures répétées pour chaque cible
        repeatability_errors = []
        
        for target_idx in range(len(profile.targets)):
            measurements = []
            
            for series_data in series:
                if target_idx < len(series_data.measurements):
                    measurements.append(series_data.measurements[target_idx])
            
            if len(measurements) >= 2:
                # Calculer l'écart-type
                mean = sum(measurements) / len(measurements)
                variance = sum((x - mean) ** 2 for x in measurements) / (len(measurements) - 1)
                std_dev = math.sqrt(variance)
                repeatability_errors.append(std_dev)
        
        return max(repeatability_errors) if repeatability_errors else 0.0
    
    def _calculate_hysteresis_error(self, profile: ComparatorProfile, 
                                   ascending: List[MeasureSeries], 
                                   descending: List[MeasureSeries]) -> float:
        """Calcule l'erreur d'hystérésis."""
        hysteresis_errors = []
        
        for target_idx, target_value in enumerate(profile.targets):
            # Moyennes des mesures montantes et descendantes
            asc_measurements = []
            desc_measurements = []
            
            for series in ascending:
                if target_idx < len(series.measurements):
                    asc_measurements.append(series.measurements[target_idx])
            
            for series in descending:
                if target_idx < len(series.measurements):
                    desc_measurements.append(series.measurements[target_idx])
            
            if asc_measurements and desc_measurements:
                asc_mean = sum(asc_measurements) / len(asc_measurements)
                desc_mean = sum(desc_measurements) / len(desc_measurements)
                hysteresis = abs(asc_mean - desc_mean)
                hysteresis_errors.append(hysteresis)
        
        return max(hysteresis_errors) if hysteresis_errors else 0.0
    
    def _calculate_Emt(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> float:
        """Calcule l'erreur de mesure totale (Emt)."""
        # Emt = erreur de linéarité + erreur de répétabilité
        linearity = self._calculate_linearity_error(profile, series)
        repeatability = self._calculate_repeatability_error(profile, series)
        return linearity + repeatability
    
    def _calculate_Eml(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> float:
        """Calcule l'erreur de mesure locale (Eml)."""
        # Eml = erreur de linéarité (approximation)
        return self._calculate_linearity_error(profile, series)
    
    def _calculate_Ef(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> float:
        """Calcule l'erreur de fidélité (Ef)."""
        # Ef = erreur de répétabilité
        return self._calculate_repeatability_error(profile, series)
    
    def _calculate_Eh(self, profile: ComparatorProfile, 
                      ascending: List[MeasureSeries], 
                      descending: List[MeasureSeries]) -> float:
        """Calcule l'erreur d'hystérésis (Eh)."""
        return self._calculate_hysteresis_error(profile, ascending, descending)
    
    def _calculate_target_stats(self, profile: ComparatorProfile, series: List[MeasureSeries]) -> List[Dict[str, float]]:
        """Calcule les statistiques pour chaque cible."""
        stats = []
        
        for target_idx, target_value in enumerate(profile.targets):
            measurements = []
            
            for series_data in series:
                if target_idx < len(series_data.measurements):
                    measurements.append(series_data.measurements[target_idx])
            
            if measurements:
                mean = sum(measurements) / len(measurements)
                variance = sum((x - mean) ** 2 for x in measurements) / len(measurements)
                std_dev = math.sqrt(variance)
                min_val = min(measurements)
                max_val = max(measurements)
                
                stats.append({
                    "target": target_value,
                    "mean": mean,
                    "std_dev": std_dev,
                    "min": min_val,
                    "max": max_val,
                    "error": abs(mean - target_value),
                    "range": max_val - min_val
                })
            else:
                stats.append({
                    "target": target_value,
                    "mean": 0.0,
                    "std_dev": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "error": 0.0,
                    "range": 0.0
                })
        
        return stats


def calculate_comparator_errors(profile: ComparatorProfile, series: List[MeasureSeries]) -> ErrorResults:
    """
    Fonction utilitaire pour calculer les erreurs d'un comparateur.
    
    Args:
        profile: Profil du comparateur
        series: Séries de mesures
    
    Returns:
        ErrorResults avec toutes les erreurs calculées
    """
    calculator = ErrorCalculator()
    return calculator.calculate_errors(profile, series)
