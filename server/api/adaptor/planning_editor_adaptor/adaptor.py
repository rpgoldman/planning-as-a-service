import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import parser_functions
from action_plan_parser.parser import Problem
import copy
import json
import re
import traceback
TEMPLATE={
    "status":"ok",
    "result":{
        "output":"None",
        "parse_status": "ok",
        "type": "full",
         "length": 0,
         "plan":[],
         "planPath":"None",
         "logPath":"None"
    }
}

class PlanningEditorAdaptor:
    def __init__(self):
        pass

    def generate_error_result(self):
        pass

    def transform(self,**kwargs):
        raw_data=kwargs["result"]

        # When the solver could not solve the problem
        if len(raw_data["stderr"])>0:
            result = copy.deepcopy(TEMPLATE)
            result["status"]="error"
            result["result"]["output"]=raw_data["stderr"]
            result["result"]["parse_status"]="error"
            return result


        else:
            #When the adaptor cloud parse the plan
            try:
                
                # Orginal arguments data(input data defined in manifest) send to the worker
                arguments=kwargs["arguments"]
                # request data send to the check API. 
                # request_data=kwargs["request_data"]

                #todo deal with multiple plans
                domain_file=arguments["domain"]["value"]
                for plan_name in raw_data["output"]:
                    actions=raw_data["output"][plan_name]
                    actions=actions.lower()
                    
                domain=Problem(domain_file)
                plan = []
                act_map = {}
                for a in domain.actions:
                    act_map[a.name] = a
                

                action_list=re.findall(r"(\([a-z -]*\))", actions)
                for action_str in action_list:
                    elements=[element for element in action_str[1:-1].split(" ") if len(element)>0]
                    a_name=elements[0]
                    if len(elements)>0:
                        a_params=elements[1:]
                    else:
                        a_params=False
                    
                    if a_name in act_map:
                        a = act_map[a_name]
                        plan.append({"name": action_str, "action": a.export(grounding=a_params)})

                result = copy.deepcopy(TEMPLATE)
                result["result"]["length"]=len(plan)
                result["result"]["plan"]=plan
                result["result"]["output"]=raw_data["stdout"]
                
                return result

            # Then the adaptor could not parse the plan, generate one action with the plan text
            except Exception:
                result = copy.deepcopy(TEMPLATE)
                result["status"]="ok"
                result["result"]["parse_status"]="ok"
                for plan_name in raw_data["output"]:
                    actions=raw_data["output"][plan_name]
                plan=[]
                plan.append({"name":"Raw Result","action":actions})
                result["result"]["plan"]=plan
                result["result"]["length"]=1
                result["result"]["output"]=raw_data["stdout"]

                return result
