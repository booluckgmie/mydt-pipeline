"""Visible labels for the template in English, French, Spanish, Portuguese and Russian.

Only text a country reads is translated. Sheet names, level codes (ISCED1..3), sex codes (M/F/T)
and the OK/CHECK flags stay language-neutral because formulas, the reader and the validator
depend on them, so every language version is processed by exactly the same code.

DRAFT translations: have a native-speaking UIS colleague review them before a survey launch.
"""
from __future__ import annotations

LANGS = ("en", "fr", "es", "pt", "ru")

_KEYS = ("title", "fill_note", "sheets_note", "meta_fields", "level", "age", "all",
         "enrol_title", "pop_title", "ind_title", "check_title", "year", "negative_cells", "status")

_T = {
    "en": ("MYDT demo template (SYNTHETIC - not the official UIS tool)",
           "Yellow cells: data entry. Grey cells: formulas - do not edit.",
           "Sheets: Metadata, Enrolment (by level/age/sex), Population, Indicators, Checks.",
           ["Country", "ISO3", "Survey year", "Contact name", "Contact email"],
           "Level", "Age", "All",
           "Enrolment by level, single age and sex",
           "School-age population by single age and sex",
           "Indicators (formulas) - GER/NER in %, GPI = F/M of GER",
           "Built-in validation checks", "Year", "Negative cells", "Status"),
    "fr": ("Modèle MYDT de démonstration (SYNTHÉTIQUE - pas l'outil officiel de l'ISU)",
           "Cellules jaunes : saisie des données. Cellules grises : formules - ne pas modifier.",
           "Feuilles : Metadata, Enrolment (par niveau/âge/sexe), Population, Indicators, Checks.",
           ["Pays", "ISO3", "Année de l'enquête", "Nom du contact", "Courriel du contact"],
           "Niveau", "Âge", "Tous",
           "Effectifs scolarisés par niveau, âge simple et sexe",
           "Population d'âge scolaire par âge simple et sexe",
           "Indicateurs (formules) - TBS/TNS en %, IPS = F/M du TBS",
           "Contrôles de validation intégrés", "Année", "Cellules négatives", "Statut"),
    "es": ("Plantilla MYDT de demostración (SINTÉTICA - no es la herramienta oficial del IEU)",
           "Celdas amarillas: entrada de datos. Celdas grises: fórmulas - no modificar.",
           "Hojas: Metadata, Enrolment (por nivel/edad/sexo), Population, Indicators, Checks.",
           ["País", "ISO3", "Año de la encuesta", "Nombre del contacto", "Correo del contacto"],
           "Nivel", "Edad", "Todos",
           "Matrícula por nivel, edad simple y sexo",
           "Población en edad escolar por edad simple y sexo",
           "Indicadores (fórmulas) - TBM/TNM en %, IPG = F/M de la TBM",
           "Controles de validación integrados", "Año", "Celdas negativas", "Estado"),
    "pt": ("Modelo MYDT de demonstração (SINTÉTICO - não é a ferramenta oficial do UIS)",
           "Células amarelas: entrada de dados. Células cinzentas: fórmulas - não editar.",
           "Folhas: Metadata, Enrolment (por nível/idade/sexo), Population, Indicators, Checks.",
           ["País", "ISO3", "Ano do inquérito", "Nome do contacto", "E-mail do contacto"],
           "Nível", "Idade", "Todos",
           "Matrículas por nível, idade simples e sexo",
           "População em idade escolar por idade simples e sexo",
           "Indicadores (fórmulas) - TBM/TLM em %, IPG = F/M da TBM",
           "Verificações de validação integradas", "Ano", "Células negativas", "Estado"),
    "ru": ("Демонстрационный шаблон MYDT (СИНТЕТИЧЕСКИЙ - не официальный инструмент ИС ЮНЕСКО)",
           "Жёлтые ячейки: ввод данных. Серые ячейки: формулы - не редактировать.",
           "Листы: Metadata, Enrolment (по уровню/возрасту/полу), Population, Indicators, Checks.",
           ["Страна", "ISO3", "Год обследования", "Контактное лицо", "Эл. почта контактного лица"],
           "Уровень", "Возраст", "Все",
           "Численность учащихся по уровню, возрасту и полу",
           "Численность населения школьного возраста по возрасту и полу",
           "Показатели (формулы) - ВКП/ЧКП в %, ИГП = Ж/М от ВКП",
           "Встроенные проверки данных", "Год", "Отрицательные значения", "Статус"),
}


def labels(lang: str = "en") -> dict:
    if lang not in _T:
        raise ValueError(f"unsupported language {lang!r}; choose from {', '.join(LANGS)}")
    return dict(zip(_KEYS, _T[lang]))
