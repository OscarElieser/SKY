"""Optional real cognitive specialists (CrewAI, AutoGen, LangChain) within SKY.

No independent tools, shell, publishing, files, email or browser access.
Only LM Studio at 127.0.0.1 may receive prompts through these adapters.
SKY remains supervisor and returns the final response to the owner.
"""
from __future__ import annotations
import asyncio
import importlib.util
import os
import re
from .sky_lmstudio import configured, _base, status as lm_status

AVAILABLE={"crewai":"crewai","autogen":"autogen_agentchat","langchain":"langchain_openai"}

class FrameworkUnavailable(RuntimeError):pass
class FrameworkInvalid(ValueError):pass

def configured_frameworks():
    result={}
    for name,mod in AVAILABLE.items():
        try:installed=importlib.util.find_spec(mod) is not None
        except (ImportError,ValueError):installed=False
        result[name]={"installed":installed,
                      "enabled":os.getenv("SKY_FRAMEWORK_"+name.upper()+"_ENABLED","0")=="1",
                      "model_configured":configured(),
                      "role":"text_only_internal_specialist",
                      "can_execute_tools":False}
    return {"controller":"SKY","frameworks":result,"local_only_model":True}

def _validate(framework,question):
    if framework not in AVAILABLE:
        raise FrameworkInvalid("Framework no admitido.")
    if not isinstance(question,str) or not 12<=len(question.strip())<=1600:
        raise FrameworkInvalid("La consulta debe tener entre 12 y 1600 caracteres.")
    cfg=configured_frameworks()["frameworks"][framework]
    if not cfg["enabled"] or not cfg["installed"] or not configured():
        raise FrameworkUnavailable("El framework o modelo local no están instalados o habilitados.")
    model=os.getenv("SKY_LMSTUDIO_MODEL","").strip()
    if not model or len(model)>150:
        raise FrameworkUnavailable("Falta configurar el modelo real de LM Studio.")
    return model

def consult(framework,question):
    model=_validate(framework,question)
    prompt=question.strip()
    instruction=("Eres especialista interno de SKY. Responde en español con análisis original, "
                 "límites, riesgos y siguientes pasos concretos. No afirmes que ejecutaste "
                 "herramientas ni que verificaste información en Internet. "
                 "No solicites secretos ni acciones externas.")
    url=_base()+"/v1"
    try:
        if framework=="langchain":
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage,HumanMessage
            chat=ChatOpenAI(model=model,base_url=url,api_key="lm-studio",
                            temperature=0.3,max_retries=0,timeout=60,
                            use_responses_api=False)
            response=chat.invoke([SystemMessage(content=instruction),
                                  HumanMessage(content=prompt)])
            answer=response.content
            if not isinstance(answer,str):
                raise FrameworkUnavailable("LangChain no entregó texto.")
        elif framework=="crewai":
            from crewai import Agent,Task,Crew,Process,LLM
            llm=LLM(model=model,custom_openai=True,base_url=url,api_key="lm-studio")
            agent=Agent(role="SKY especialista",goal="Analizar una tarea sin ejecutarla",
                        backstory="Asesor cognitivo interno bajo supervisión SKY.",
                        llm=llm,tools=[],allow_delegation=False,max_iter=1,verbose=False)
            task=Task(description=instruction+"\nSolicitud: "+prompt,
                      expected_output="Explicación técnica verificable, sin acciones externas.",
                      agent=agent)
            crew=Crew(agents=[agent],tasks=[task],process=Process.sequential,verbose=False)
            answer=str(crew.kickoff())
        else:
            from autogen_agentchat.agents import AssistantAgent
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            async def run():
                client=OpenAIChatCompletionClient(
                    model=model,base_url=url,api_key="lm-studio",
                    model_info={"vision":False,"function_calling":False,
                                "json_output":False,"family":"unknown",
                                "structured_output":False})
                try:
                    agent=AssistantAgent(name="sky_specialist",model_client=client,
                                         tools=[],max_tool_iterations=1,
                                         system_message=instruction)
                    result=await agent.run(task=prompt)
                    messages=getattr(result,"messages",[])
                    return str(getattr(messages[-1],"content","")) if messages else ""
                finally:
                    await client.close()
            answer=asyncio.run(run())
        if not isinstance(answer,str) or not answer.strip() or len(answer)>30000:
            raise FrameworkUnavailable("El especialista local no entregó texto válido.")
        return {"controller":"SKY","framework":framework,"provider":"lmstudio_local",
                "message":answer.strip(),"executed_external_actions":False}
    except FrameworkUnavailable:
        raise
    except Exception as exc:
        # SDK errors can carry sensitive prompts/paths/tokens; never echo.
        raise FrameworkUnavailable("Falló el framework local: revisá su versión y LM Studio.") from exc
