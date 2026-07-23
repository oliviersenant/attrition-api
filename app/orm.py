"""Tables de la base de données (SQLAlchemy ORM).

Deux tables partagent les mêmes 25 champs métier (l'input du modèle) :
- `employes`    — le dataset de référence (1470 employés + label réel) ;
- `predictions` — la trace de chaque échange avec le modèle (snapshot de
  l'input reçu + output + contexte de décision + horodatage).

Le **mixin** `ColonnesEmployeMixin` déclare ces champs UNE seule fois : pas de
duplication, et l'alignement des deux tables est garanti par construction.
`predictions` porte un *snapshot* (pas une FK vers `employes`) car l'API doit
pouvoir tracer un employé absent du dataset.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, mapped_column


class Base(DeclarativeBase):
    pass


@declarative_mixin
class ColonnesEmployeMixin:
    """Les 25 champs métier attendus par le modèle (cf. app/schemas.py)."""

    # -- Source SIRH --
    age: Mapped[int]
    genre: Mapped[str] = mapped_column(String(10))
    revenu_mensuel: Mapped[float]
    statut_marital: Mapped[str] = mapped_column(String(30))
    departement: Mapped[str] = mapped_column(String(50))
    poste: Mapped[str] = mapped_column(String(50))
    nombre_experiences_precedentes: Mapped[int]
    annee_experience_totale: Mapped[int]
    annees_dans_l_entreprise: Mapped[int]
    annees_dans_le_poste_actuel: Mapped[int]

    # -- Source EVAL --
    satisfaction_employee_environnement: Mapped[int]
    note_evaluation_precedente: Mapped[int]
    satisfaction_employee_nature_travail: Mapped[int]
    satisfaction_employee_equipe: Mapped[int]
    satisfaction_employee_equilibre_pro_perso: Mapped[int]
    heure_supplementaires: Mapped[str] = mapped_column(String(5))
    augementation_salaire_precedente: Mapped[float]

    # -- Source SONDAGE --
    nombre_participation_pee: Mapped[int]
    nb_formations_suivies: Mapped[int]
    distance_domicile_travail: Mapped[float]
    niveau_education: Mapped[int]
    domaine_etude: Mapped[str] = mapped_column(String(50))
    frequence_deplacement: Mapped[str] = mapped_column(String(20))
    annees_depuis_la_derniere_promotion: Mapped[int]
    annes_sous_responsable_actuel: Mapped[int]


class Employe(ColonnesEmployeMixin, Base):
    """Le dataset de référence, tel que fourni par les 3 sources jointes."""

    __tablename__ = "employes"

    id_employee: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    a_quitte_l_entreprise: Mapped[int]  # label réel : 1 = a quitté, 0 = est resté


class Prediction(ColonnesEmployeMixin, Base):
    """Trace d'un échange avec le modèle : input reçu + output + contexte."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    probabilite_depart: Mapped[float]
    prediction: Mapped[int]  # décision au seuil : 1 = risque de départ
    seuil: Mapped[float]
    version_modele: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
