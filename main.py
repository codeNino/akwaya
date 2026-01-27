from internal.domain.pipeline.augmentation import trigger_leads_information_augmentation
from internal.domain.pipeline.ingestion import trigger_leads_sourcing
from internal.config.secret import validate_environment
from internal.config.paths_config import (LEADS_SOURCED_PATH, LEADS_AUGMENTED_PATH)

validate_environment(
    ["SERPER_API_KEY", "GOOGLE_API_KEY", "OPENAI_KEY"]
)
    
def main(): 

    # trigger_leads_sourcing(
    #     "Find me companies who have attended a Forex Expo in the last 2 years", 
    #     LEADS_SOURCED_PATH
    # )    
    trigger_leads_information_augmentation(
        LEADS_SOURCED_PATH,
        LEADS_AUGMENTED_PATH
    )    
    


if __name__ == "__main__":
    main()
