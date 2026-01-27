from langchain_core.prompts import ChatPromptTemplate


keyword_generation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a keyword generation engine for a leads generation and acquisition system. \
     You will be given a query and you will return a list of keywords that can be used to find relevant information on the web.\
        Below is an example query and the expected output:  \n \
            query: 'Find me forex brokers in Cyprus',\
            output: ['forex brokers Cyprus', 'Cyprus forex brokers', 'Cyprus forex companies', \
                'Cyprus forex firms', 'Cyprus forex providers', \
                    'Cyprus forex online trading companies']"),
    ("user", "{query}"),
])

sourced_leads_preprocessing_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at analysing and preprocessing leads sourced from the internet.\
        Your task is to prevent duplicates, ensure that highly relevant leads alone are returned, \
            and also to classify the valid leads into 3 major categories:\n \
                1. Individuals, 2. Businesses, 3. Blogs/Articles \n\
            "),
    ("user", "{leads}"),
])

scraped_website_evaluation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at analysing and evaluating scraped website data. \n\
        Your task is to extract relevant information from the scraped website data, summarize where necessary and return it in a structured format. \n\
        The structured format should include the following fields: \n\
            1. email: Optional[str] \n\
            2. phone: Optional[str] \n\
            3. about: Optional[str] \n\
        return the exact url that came with the website data\
    "),
    ("user", "{website_data}"),
])

leads_extraction_from_articles_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at extracting businesses and individuals from data scraped from articles. \
        Your task is to extract relevant information (keywords e.g names + locations + context) about businesses or individuals that can be \
           used to search for them on the internet.\
            What you extract will be used as a query to source for more information about the leads\
                on the internet.\
                    BEWARE THAT THE KEYWORDS ARE EXPECTED TO MATCH TO UNIQUE ENTITIES SO TWO KEYWORDS \
                        SHOULD NOT DESCRIBE THE SAME ENTITY DIFFERENTLY. AVOID DUPLICATES."),    
    ("user", "{scraped_data}"),
])
    