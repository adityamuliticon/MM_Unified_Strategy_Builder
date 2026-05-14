import json
import requests
from config import Config
from services.generator import generator
from services.market_maya import market_maya

def test_deploy():
    print("Testing Strategy Deployment via Command Line...")
    
    # 1. Define strategy parameters (Sample Straddle)
    main_params = {
        "strategyName": "CLI_Test_Strategy",
        "underlying": "NIFTY",
        "mainExchange": "NSE",
        "mainSegment": "OPTIDX",
        "mainSymbol": "NIFTY",
        "isIntraday": True,
        "productType": "MIS",
        "tradingStartTime": "09:20:00",
        "tradingEndTime": "15:15:00",
        "isEnableMasterTarget": True,
        "targetBy": "Combined Profit",
        "intradayTarget": 2500,
        "isEnableMasterSl": True,
        "slBy": "Combined Loss",
        "intradaySl": 1500
    }
    
    legs = [
        {
            "tradeSide": "SELL",
            "lot": 1,
            "segment": "OPT",
            "optionType": "CE",
            "atmType": "Strike By ATM Value",
            "atm": 0
        },
        {
            "tradeSide": "SELL",
            "lot": 1,
            "segment": "OPT",
            "optionType": "PE",
            "atmType": "Strike By ATM Value",
            "atm": 0
        }
    ]
    
    # 2. Generate Payload
    print("Generating V3 Payload...")
    payload = generator.generate_v3_payload(main_params, legs)
    
    # 3. Deploy
    print(f"Deploying to {Config.CREATE_STRATEGY_URL}...")
    result = market_maya.deploy_strategy(payload)
    
    print("\nDeployment Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_deploy()
