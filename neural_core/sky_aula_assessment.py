"""SKY Aula assessment instruments with saber conocer, hacer, ser/convivir.

Produces editable teacher instruments, not ungrounded numerical marks.
Rubric scoring requires human recorded performance on explicit criteria.
No learner name, ID, medical data or answers persisted.
"""
from __future__ import annotations

import re

DIMENSIONS={
  "conocer":("Saber conocer","Comprende conceptos, vocabulario, causas y relaciones"),
  "hacer":("Saber hacer","Aplica procedimientos, resuelve casos y demuestra habilidades"),
  "ser":("Saber ser y convivir","Actúa con responsabilidad, colaboración, respeto y seguridad"),
}
LEVELS=[
  {"level":4,"name":"Destacado","descriptor":"Lo demuestra con autonomía, precisión y explicación de sus decisiones"},
  {"level":3,"name":"Logrado","descriptor":"Lo demuestra correctamente con apoyo ocasional"},
  {"level":2,"name":"En proceso","descriptor":"Lo demuestra parcialmente; requiere acompañamiento"},
  {"level":1,"name":"Inicial","descriptor":"Todavía no demuestra evidencia suficiente; necesita apoyo guiado"},
]
TYPES=("diagnostica","formativa","sumativa")
INSTRUMENTS=("rubrica","lista_cotejo","guia_observacion",
             "ticket_salida","estudio_caso","portafolio","autoevaluacion",
             "coevaluacion","prueba_practica","cuestionario")
class AssessmentInput(ValueError):pass

def _text(value,maximum=200):
    if not isinstance(value,str) or not 3<=len(value.strip())<=maximum:
        raise AssessmentInput("Escribí un texto de 3 a "+str(maximum)+" caracteres.")
    if any(ord(x)<32 for x in value):raise AssessmentInput("No se admiten caracteres de control.")
    return " ".join(value.split())

def build(topic:str,level:str,goal:str,*,evaluation_type:str="formativa",
          instrument:str="rubrica",criteria:dict|None=None,
          weights:dict[str,int]|None=None)->dict:
    from .sky_aula import LEVELS as EDUCATION_LEVELS
    topic=_text(topic,160)
    goal=_text(goal,300)
    if level not in EDUCATION_LEVELS:raise AssessmentInput("Nivel académico no reconocido.")
    if evaluation_type not in TYPES or instrument not in INSTRUMENTS:
        raise AssessmentInput("Evaluación o instrumento desconocido.")
    if criteria is None:
        criteria={
          "conocer":"Explica las ideas centrales de "+topic,
          "hacer":"Demuestra una aplicación segura de "+topic+" mediante un caso real",
          "ser":"Participa responsablemente, escucha y respeta a sus compañeros",
        }
    if not isinstance(criteria,dict) or set(criteria)!=set(DIMENSIONS):
        raise AssessmentInput("Indicá un criterio de conocer, hacer y ser/convivir.")
    clean={k:_text(v,220) for k,v in criteria.items()}
    # Weightings are suggestions only: only the teacher can approve final grades.
    if weights is None:
        weighted={"conocer":30,"hacer":50,"ser":20}
    else:
        if (not isinstance(weights,dict) or set(weights)!=set(DIMENSIONS)
                or any(type(v) is not int or v<0 or v>100 for v in weights.values())
                or sum(weights.values())!=100):
            raise AssessmentInput("Los tres pesos deben ser enteros entre 0 y 100, y sumar 100.")
        weighted={key:weights[key] for key in DIMENSIONS}
    out={"topic":topic,"level":level,"goal":goal,"type":evaluation_type,
         "instrument":instrument,"curriculum_verified":False,
         "teacher_must_approve_before_grading":True,
         "personal_student_data_persisted":False,
         "dimensions":[],"weights_suggested_pct":weighted,
         "criteria_reference":"draft_for_teacher_validation",
         "evidence_needed":"observación real o productos del aprendizaje"}
    for key,(name,desc) in DIMENSIONS.items():
        row={"dimension":key,"label":name,"criterion":clean[key],
             "description":desc,"weight_suggested_pct":weighted[key]}
        if instrument=="rubrica":
            row["levels"]=[{"value":x["level"],"label":x["name"],
                            "descriptor":x["descriptor"]+" en el criterio: "+clean[key]}
                           for x in LEVELS]
        elif instrument=="lista_cotejo":
            row["options"]=["Sí demuestra","Aún no demuestra","No observado"]
        elif instrument=="guia_observacion":
            row["options"]=["Observado","Parcial","No observado"]
            row["record_evidence"]=["hecho observado","situación","apoyos","siguiente paso"]
        else:
            row["prompt"]="¿Qué evidencia real permite comprobar que "+clean[key].lower()+"?"
        out["dimensions"].append(row)
    return out

def evaluate(instrument:dict,observations:dict,*,teacher_approved:bool=False)->dict:
    if teacher_approved is not True:
        raise AssessmentInput("La calificación final debe aprobarla la persona docente.")
    if not isinstance(instrument,dict) or instrument.get("instrument")!="rubrica":
        raise AssessmentInput("Para puntuación se requiere una rúbrica válida.")
    rows=instrument.get("dimensions")
    if not isinstance(rows,list) or len(rows)!=3 or {x.get("dimension") for x in rows}!=set(DIMENSIONS):
        raise AssessmentInput("La rúbrica debe contener los tres saberes.")
    if not isinstance(observations,dict) or set(observations)!=set(DIMENSIONS):
        raise AssessmentInput("Faltan evidencias para los tres saberes.")
    result=[];grade=0.
    for row in rows:
        key=row["dimension"]
        o=observations[key]
        if not isinstance(o,dict) or type(o.get("level")) is not int or o["level"] not in (1,2,3,4):
            raise AssessmentInput("Nivel de desempeño inválido.")
        evidence=_text(o.get("evidence",""),500)
        weight=row.get("weight_suggested_pct")
        if type(weight) is not int or not 0 <= weight <= 100:
            raise AssessmentInput("Peso de evaluación inválido.")
        grade+=(o["level"]/4)*weight
        result.append({"dimension":key,"observed_level":o["level"],"evidence":evidence,
                       "suggested_weight_pct":weight})
    if sum(r["suggested_weight_pct"] for r in result)!=100:
        raise AssessmentInput("Los pesos deben sumar 100.")
    return {"score_pct":round(grade,2),"scored_against_teacher_observations":True,
            "official_grade":False,"teacher_approved":True,
            "dimension_results":result,"student_identifiers_stored":False,
            "feedback":"Reforzar los criterios con desempeño menor que 3 y registrar nuevas evidencias."}

def alternatives()->dict:
    return {"types":TYPES,"instruments":INSTRUMENTS,
            "dimensions":[{"id":k,"label":v[0],"purpose":v[1]} for k,v in DIMENSIONS.items()],
            "methods":["diagnóstico inicial","pregunta socrática","tarea auténtica",
                 "demostración guiada","evaluación entre pares","autoevaluación",
                 "portafolio","lista de cotejo","rúbrica analítica","guía de observación",
                 "ticket de salida","estudio de caso","proyecto integrador"],
            "assessment_principles":["inclusión y ajustes razonables","evaluación basada en evidencias",
                 "transparencia de criterios","retroalimentación accionable",
                 "evaluación humana para consecuencias académicas"]}
