import json
import re
from openai import OpenAI
from config import Config
from rag.retriever import retriever
from mcp.handlers import handler

class Orchestrator:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.RUNWARE_API_KEY,
            base_url=Config.RUNWARE_BASE_URL
        )
        self.model = Config.RUNWARE_MODEL_ID or "runware-latest"
        self.system_prompt = """
STRICT TWO-STEP WORKFLOW:
1. PREVIEW: You MUST provide 4 Markdown tables mirroring the UI tabs.
   - **CRITICAL RULE: SMART SUGGESTIONS.** While you must not assume values blindly, if the user asks for "profitable values", "suggest something", or gives a vague request, you SHOULD suggest a standard, well-known strategy (e.g., an ATM Straddle, Strangle, or Iron Fly).
   - When suggesting, you MUST explicitly state: "I have suggested standard values for a [Strategy Name]. Please review and confirm or modify them."
   - If the user provides a specific value (e.g., "6 legs", "VIX=true"), you MUST use that value immediately in the preview.
   - For any parameter where the user provided no input AND didn't ask for a suggestion, use "[REQUIRED]" for core fields (Underlying, Legs) and BRD defaults (0/False) for optional fields.
   
   TABLE STRUCTURES:
   - MAIN TABLE: Name, Exchange, Segment, Symbol, Trading Type, Product, Start Time, Sqroff Time, **Range Breakout (Status/Time)**, **Combined Premium Entry (Status/Value)**.
     * **STRICT RULE**: Range Breakout and Combined Premium Entry are MUTUALLY EXCLUSIVE. You cannot enable both.
   - LEGS TABLE: Leg #, Idle, Side, Lots, Segment, Expiry, Option, Strike (Type/Value), Target, SL, and **Advanced Settings (Profit Locking, Action Target, SL Trailing, Action SL, Wait & Trade, Range Breakout)**.
     * Note: If any advanced setting is active for a leg, you MUST display its details (e.g., "Range: High Break") in the table.
   - ADVANCE TABLE: Exactly 12 Sections + Required Margin:
     (1. Master Target, 2. Profit Locking, 3. Action Target, 4. Master SL, 5. SL Trailing, 6. Action SL, 7. Expiry, 8. Working Days, 9. VIX, 10-12. Flags, Required Margin).
   - DESCRIPTION: Short Description & Detailed Description.
   DO NOT suggest "fallbacks" unless you receive a real error.
   If a user asks for 10 legs, you MUST generate 10 distinct legs.
   DO NOT call `create_and_deploy_strategy` yet. Ask: "Shall I proceed?"
2. EXECUTION: ONLY after approval, call `create_and_deploy_strategy`.

STRICT JSON SCHEMA:
{
  "tool": "create_and_deploy_strategy",
  "arguments": {
    "strategy_json": {
        "strategyName": "<string>",
        "underlying": "NIFTY/BANKNIFTY",
        "shortDescription": "<one_liner>",
        "detailedDescription": "<full_logic>",
        "productType": "MIS/NRML",
        "entry_time": "HH:MM:SS",
        "exit_time": "HH:MM:SS",
        "intradayTarget": <number>,
        "intradaySl": <number>,
        "trailing_sl": <number_or_object>,
        "trading_days": [<list_of_days>],
        "sqroff_all_legs": <boolean>,
        "sqroff_on_rejection": <boolean>,
        "vix_filter": <boolean>,
        "vix_start_value": <number>,
        "vix_end_value": <number>,
        "is_range_breakout": <boolean>,
        "range_end_time": "HH:MM:SS",
        "sqroff_before_expiry": <boolean>,
        "sqroff_before_expiry_days": <number>,
        "reexecute_on_target_count": <number>,
        "reexecute_on_target_delay": <number>,
        "reexecute_on_sl_count": <number>,
        "reexecute_on_sl_delay": <number>,
        "is_btst_stbt": <boolean>,
        "btst_gap_days": <number>,
        "master_profit_locking": {
            "if_profit_reaches": <number>,
            "lock_minimum_profit": <number>,
            "increse_in_profit_by": <number>,
            "trail_profit_by": <number>,
            "no_of_time_trail": <number>
        },
        "legs": [
            { 
                "is_idle": <boolean>,
                "action": "BUY/SELL", 
                "option": "CE/PE", 
                "strike_type": "ATM / ATM% / PREMIUM_RANGE / NEAREST_PREMIUM / DELTA_RANGE / NEAREST_DELTA / THETA_RANGE / NEAREST_THETA",
                "strike": "ATM Offset or Value", 
                "lots": <number>, 
                "direction": "BOTH/ITM/OTM",
                "condition": "Any / AboveEqual / BelowEqual",
                "target": <number>, 
                "target_by": "Money/Point/Point%",
                "sl": <number>,
                "sl_by": "Money/Point/Point%",
                "wait_and_trade": <boolean>,
                "wait_for": "Up % / Down % / Up pts / Down pts",
                "wait_value": <number>,
                "trail_sl": {
                    "increase_profit_by": <number>,
                    "trail_sl_by": <number>,
                    "no_of_time_trail": <number>
                },
                "profit_locking": {
                    "if_profit_reaches": <number>,
                    "lock_minimum_profit": <number>,
                    "increse_in_profit_by": <number>,
                    "trail_profit_by": <number>,
                    "no_of_time_trail": <number>
                },
                "action_on_target": "Execute Leg / Reenter Leg / Sqroff Leg",
                "target_action_leg_no": <number>,
                "target_action_delay": <number>,
                "action_on_sl": "Execute Leg / Reenter Leg / Sqroff Leg",
                "sl_action_leg_no": <number>,
                "sl_action_delay": <number>
                "is_execute_on_range_breakout": <boolean>,
                "execute_on_range_breakout": "Range High Break / Range Low Break"
            }
        ]
    }
  }
}
"""

    def process_message(self, user_message, history=None):
        if history is None:
            history = []
            
        # Get context from RAG
        context = retriever.get_context(user_message)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Relevant Documentation Context:\n{context}"}
        ] + history + [{"role": "user", "content": user_message}]
        
        # Loop for multi-step tool calls
        max_turns = 10
        executed_tools = set()
        
        for turn in range(max_turns):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            content = response.choices[0].message.content
            
            # Try to parse tool call from content
            tool_called = False
            try:
                import re
                start_indices = [m.start() for m in re.finditer(r'\{', content)]
                
                for start_idx in start_indices:
                    brace_count = 0
                    end_idx = -1
                    for i in range(start_idx, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx != -1:
                        json_str = content[start_idx:end_idx]
                        try:
                            clean_json = json_str.strip('`').strip()
                            if clean_json.startswith('json'): clean_json = clean_json[4:].strip()
                            
                            data = json.loads(clean_json)
                            tool_name = None
                            args = None
                            
                            if isinstance(data, dict):
                                if "tool" in data and "arguments" in data:
                                    tool_name = data["tool"]
                                    args = data["arguments"]
                                else:
                                    # Handle direct format like {"create_and_deploy_strategy": {...}}
                                    for key in ["create_and_deploy_strategy", "validate_strategy", "get_validation_rules"]:
                                        if key in data:
                                            tool_name = key
                                            val = data[key]
                                            # Ensure args is wrapped in strategy_json if the tool expects it
                                            if tool_name in ["create_and_deploy_strategy", "validate_strategy"]:
                                                if "strategy_json" in val: args = val
                                                else: args = {"strategy_json": val}
                                            else:
                                                args = val
                                            break
                            
                            if tool_name and args:
                                args_str = json.dumps(args, sort_keys=True)
                                tool_key = f"{tool_name}:{args_str}"
                                
                                # Prevent infinite loops with same tool/args
                                if tool_key in executed_tools:
                                    print(f"!! [Turn {turn+1}] Skipping redundant tool call: {tool_name}")
                                    continue
                                
                                executed_tools.add(tool_key)
                                print(f"> [Turn {turn+1}] Executing tool: {tool_name}")
                                tool_result = handler.handle_tool_call(tool_name, args)
                                
                                messages.append({"role": "assistant", "content": content})
                                messages.append({
                                    "role": "user", 
                                    "content": f"SYSTEM TOOL RESULT: {json.dumps(tool_result)}"
                                })
                                tool_called = True
                                
                                # CRITICAL: If deployment succeeded, stop the loop to prevent double-execution
                                if tool_name == "create_and_deploy_strategy" and tool_result.get("status") == "success":
                                    clean_summary = re.sub(r'\{.*\}', '', content, flags=re.DOTALL).strip()
                                    if not clean_summary: clean_summary = content
                                    return clean_summary + "\n\n**Strategy Deployed Successfully.**"
                                    
                                break 
                        except Exception as e:
                            print(f"JSON inner parsing error: {e}")
                            continue
                
                if tool_called:
                    continue
            except Exception as e:
                print(f"Tool parsing/execution error: {e}")
            
            # Clean up content for UI (remove JSON blocks)
            ui_content = re.sub(r'\{.*\}', '', content, flags=re.DOTALL).strip()
            # If nothing left, use a default summary or the original content if no JSON was found
            if not ui_content: ui_content = content
            
            return ui_content
        
        # If we hit the limit, try to get a final summary from the AI
        messages.append({"role": "user", "content": "You have done enough research. Please provide the final strategy summary and ask for deployment confirmation now."})
        final_attempt = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return final_attempt.choices[0].message.content

# Singleton instance
orchestrator = Orchestrator()
