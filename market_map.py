import os
import time
import google.generativeai as genai
import json
from neo4j import GraphDatabase
import requests
from bs4 import BeautifulSoup
import tempfile
import PyPDF2
import io
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from dotenv import load_dotenv

load_dotenv()

def configure():
    """Configure the Gemini API with your API key."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=api_key)

def scrape_website(url):
    """Scrape the content of a website."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract main content, remove scripts, styles and navigation
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        
        # Basic clean up
        text = " ".join(text.split())
        
        return text
    except Exception as e:
        print(f"Error scraping website {url}: {e}")
        return None

def find_and_read_pdf(pdf_path, max_pages_per_pdf=None):
    """Find PDF with company info and read its content."""
    pdf_contents = []
    try:
            print(f"Processing PDF: {pdf_path}")
            
            # Extract text from PDF
            pdf_reader = PyPDF2.PdfReader(pdf_path)
            pdf_text = ""
            
            # Determine how many pages to process
            pages_to_process = len(pdf_reader.pages)
            if max_pages_per_pdf is not None:
                pages_to_process = min(pages_to_process, max_pages_per_pdf)
            
            for page_num in range(pages_to_process):
                page = pdf_reader.pages[page_num]
                extracted_text = page.extract_text()
                if extracted_text:
                    pdf_text += extracted_text + " "
            
            if pdf_text.strip():  # Only add if we got some text
                pdf_contents.append({
                    "path": pdf_path,
                    "text": pdf_text.strip()
                })
                print(f"Successfully extracted {pages_to_process} pages from {pdf_path}")
            else:
                print(f"Warning: No text could be extracted from {pdf_path}")
                
    except Exception as e:
        print(f"Error processing PDF file {pdf_path}: {e}")
    
    return pdf_contents
        

def upload_text_as_file(text, filename="website_content.txt"):
    """Upload text content to Gemini."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp:
        temp.write(text)
        temp_path = temp.name
    
    try:
        # Upload the file to Gemini
        file = genai.upload_file(temp_path, display_name=filename)
        print(f"Uploaded text as file '{file.display_name}' with URI: {file.uri}")
        
        # Wait for file processing
        while True:
            file_status = genai.get_file(file.name)
            if file_status.state.name == "ACTIVE":
                break
            elif file_status.state.name != "PROCESSING":
                raise Exception(f"File {file.name} failed to process")
            print("Waiting for file processing...")
            time.sleep(5)
        
        print("File is ready for use.")
        return file
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def query_gemini(file, prompt):
    """Sends a file and prompt to Gemini and returns the response."""
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        },
    )

    response = model.generate_content([file, prompt])
    return json.loads(response.text)

def process_website_with_prompts(url, pdf_path=None):
    """Scrapes a website, finds PDFs, and queries Gemini with multiple prompts."""
    # Scrape the main website content
    print(f"Scraping website: {url}")
    website_content = scrape_website(url)
    
    # Process PDF if provided
    pdf_contents = []
    if pdf_path:
        print(f"Processing provided PDF: {pdf_path}")
        if os.path.exists(pdf_path):
            pdf_contents = find_and_read_pdf(pdf_path)
        else:
            print(f"Warning: PDF file '{pdf_path}' not found. Continuing without PDF data.")
    
    # Combine all content
    all_content = website_content or ""
    
    # Add PDF content if available
    if pdf_contents:
        for pdf in pdf_contents:
            all_content += f"\n\nPDF Content from {pdf['path']}:\n{pdf['text']}"
    
    # Upload content as a file
    file = upload_text_as_file(all_content, filename=f"content_from_{url.replace('https://', '').replace('http://', '').replace('/', '_')}.txt")
    
    # Define prompts to extract information
    prompts = {
        "company_info": """Extract the company's name and its core mission or product from the website content.
        Return the result in the following JSON format:
        {
            "company_name": "<Company Name>",
            "mission_or_product": "<Mission or Product>"
        }""",

        "problem_solution": """Identify the problem the company is trying to solve and the solution they offer.
        Return the result in the following JSON format:
        {
            "problem": "<Problem Statement>",
            "solution": "<Solution Offered>"
        }""",

        "key_people": """Identify key individuals and their roles within the company (e.g., Founder, CEO, CTO).
        Return the result in the following JSON format:
        {
            "key_people": [
                {
                    "name": "<Name>",
                    "role": "<Role>"
                }
            ]
        }""",

        "investors": """Look carefully and List the investors mentioned, including individual investors and firms, along with any details.
        Return the result in the following JSON format:
        {
            "investors": [
                {
                    "investor_name": "<Investor Name>",
                    "investment_amount": "<Investment Amount>"
                }
            ]
        }""",

        "market_segments": """Identify the market segments or industries the company is targeting.
        Return the result as a list of strings, like so:
        {
            "market_segments": [
                "Segment 1",
                "Segment 2",
                "Segment 3"
            ]
        }""",

        "company_roles": """List the relationships between the company and key individuals, such as founders and executives.
        Return the result in the following JSON format:
        {
            "company_roles": [
                {
                    "person_name": "<Name>",
                    "role_in_company": "<Role>"
                }
            ]
        }""",

        "employees": """Identify any employees mentioned and their roles.
        Return the result in the following JSON format:
        {
            "employees": [
                {
                    "employee_name": "<Employee Name>",
                    "employee_role": "<Role>"
                }
            ]
        }""",

        "competitors": """List competitors mentioned in the website and describe how they compete with the company.
        Return the result in the following JSON format:
        {
            "competitors": [
                {
                    "competitor_name": "<Competitor Name>",
                    "competitive_advantage": "<Competitive Advantage>"
                }
            ]
        }""",

        "customers": """Identify any companies that are customers of the company, if mentioned.
        Return the result in the following JSON format:
        {
            "customers": [
                {
                    "customer_name": "<Customer Name>",
                    "product_or_service": "<Product or Service>"
                }
            ]
        }""",

        "previous_companies": """Identify any previous companies associated with key individuals (past startups, previous employment).
        Return the result in the following JSON format:
        {
            "previous_companies": [
                {
                    "individual_name": "<Name>",
                    "company_name": "<Previous Company>",
                    "role": "<Role>"
                }
            ]
        }"""
    }

    results = {}
    for key, prompt in prompts.items():
        print(f"Processing: {key}")
        results[key] = query_gemini(file, prompt)

    # Construct structured JSON response
    structured_response = {
        "Company": results.get("company_info", {}),
        "Problem_Solution": results.get("problem_solution", {}),
        "Key People": results.get("key_people", {}),
        "Investors": results.get("investors", {}),
        "Market Segments": results.get("market_segments", {}),
        "Company Roles": results.get("company_roles", {}),
        "Employees": results.get("employees", {}),
        "Competitors": results.get("competitors", {}),
        "Customers": results.get("customers", {}),
        "Previous Companies": results.get("previous_companies", {}),
    }

    return json.dumps(structured_response, indent=4)

def map_market_segments(market_segments, category_hierarchy, threshold=0.5):
    """Maps given market segments to the best-matching category and subcategories that exceed the threshold.
       Ensures that if a subcategory is selected, its corresponding category is also included."""
    model = SentenceTransformer('all-MiniLM-L6-v2')

    categories = list(category_hierarchy.keys())
    subcategories = [sub for sublist in category_hierarchy.values() for sub in sublist]

    # Mapping from subcategories to their main categories for later use
    subcategory_to_category = {}
    for category, sublist in category_hierarchy.items():
        for sub in sublist:
            subcategory_to_category[sub] = category

    category_embeddings = model.encode(categories, convert_to_tensor=True)
    subcategory_embeddings = model.encode(subcategories, convert_to_tensor=True)

    result_set = set()

    for segment in market_segments:
        segment_embedding = model.encode(segment, convert_to_tensor=True)

        # Calculate similarity scores for categories
        category_scores = util.pytorch_cos_sim(segment_embedding, category_embeddings).squeeze()
        best_category_score = category_scores.max().item()
        best_category_idx = category_scores.argmax().item()
        best_category = categories[best_category_idx]

        # Calculate similarity scores for subcategories
        subcategory_scores = util.pytorch_cos_sim(segment_embedding, subcategory_embeddings).squeeze()
        filtered_subcategories = [subcategories[i] for i in range(len(subcategories)) if subcategory_scores[i] > threshold]

        # Add the best category only if it exceeds the threshold
        if best_category_score > threshold:
            result_set.add(best_category)

        # Add all subcategories that exceed the threshold
        for sub in filtered_subcategories:
            result_set.add(sub)
            # Ensure the main category of the subcategory is included
            result_set.add(subcategory_to_category[sub])

    return list(result_set)

class Neo4jDatabase:
    def __init__(self, uri, username=None, password=None):
        if username and password:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
        else:
            # Connection without auth - ensure this is intentional
            raise ValueError("Neo4j username and password are required for authentication")

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            session.run(query, parameters or {})

def load_data_into_neo4j(data, uri, username=None, password=None):
    # Parse data if it's a string
    if isinstance(data, str):
        data = json.loads(data)
    
    # Initialize Database Connection
    db = Neo4jDatabase(uri, username, password)

    # Insert Company
    company = data.get("Company", {})
    if company:
        # Check if company is a list or dict and handle accordingly
        if isinstance(company, list):
            # If it's a list, use the first item if available
            if company and isinstance(company[0], dict):
                company_dict = company[0]
            else:
                company_dict = {"company_name": "Unknown", "mission_or_product": "No mission provided"}
        else:
            company_dict = company
            
        company_query = """
        MERGE (c:Company {name: $name})
        ON CREATE SET c.mission = $mission
        """
        db.run_query(company_query, {
            "name": company_dict.get("company_name", "Unknown"),
            "mission": company_dict.get("mission_or_product", "No mission provided")
        })
    
    # Insert Problem and Solution
    problem_solution = data.get("Problem_Solution", {})
    if problem_solution:
        # Handle problem_solution if it's a list
        if isinstance(problem_solution, list) and problem_solution and isinstance(problem_solution[0], dict):
            problem_solution_dict = problem_solution[0]
        else:
            problem_solution_dict = problem_solution
            
        problem_solution_query = """
        MATCH (c:Company {name: $name})
        SET c.problem = $problem,
            c.solution = $solution
        """
        db.run_query(problem_solution_query, {
            "name": company_dict.get("company_name", "Unknown"),
            "problem": problem_solution_dict.get("problem", "No problem provided"),
            "solution": problem_solution_dict.get("solution", "No solution provided")
        })

    # Insert People (Key People)
    key_people = data.get("Key People", {}).get('key_people', [])
    for person in key_people:
        if not person.get("name"):
            continue  # Skip if name is missing

        person_query = """
        MERGE (p:Person {name: $name})
        ON CREATE SET p.role = $role
        """
        db.run_query(person_query, {
            "name": person["name"],
            "role": person.get("role", "Unknown Role")
        })

        relationship_type = "FOUNDED" if "founder" in person.get("role", "").lower() else "LEADS"
        relationship_query = f"""
        MATCH (p:Person {{name: $name}})
        MATCH (c:Company {{name: $company_name}})
        MERGE (p)-[:{relationship_type}]->(c)
        """
        db.run_query(relationship_query, {
            "name": person["name"],
            "company_name": company_dict.get("company_name", "Unknown")
        })

    # Insert Investors
    investors = data.get("Investors", {}).get("investors", [])
    for investor in investors:
        if not investor.get("investor_name"):
            continue  # Skip if investor's name is missing

        # Handle investment amount for investor node
        investment_amount = investor.get("investment_amount")
        if investment_amount is None or investment_amount == "":
            # Create investor node without setting investment_amount property
            investor_query = """
            MERGE (i:Investor {name: $name})
            """
            db.run_query(investor_query, {
                "name": investor["investor_name"]
            })
        else:
            # Set investment_amount property when available
            investor_query = """
            MERGE (i:Investor {name: $name})
            ON CREATE SET i.investment_amount = $investment_amount
            """
            db.run_query(investor_query, {
                "name": investor["investor_name"],
                "investment_amount": investment_amount
            })

        # Handle null investment_amount values
        investment_amount = investor.get("investment_amount")
        if investment_amount is None or investment_amount == "":
            # Create relationship without the investment_amount property if it's null
            investment_query = """
            MATCH (i:Investor {name: $name})
            MATCH (c:Company {name: $company_name})
            MERGE (i)-[:INVESTED_IN]->(c)
            """
            db.run_query(investment_query, {
                "name": investor["investor_name"],
                "company_name": company_dict.get("company_name", "Unknown")
            })
        else:
            # Include the investment_amount property when it's available
            investment_query = """
            MATCH (i:Investor {name: $name})
            MATCH (c:Company {name: $company_name})
            MERGE (i)-[:INVESTED_IN {investment_amount: $investment_amount}]->(c)
            """
            db.run_query(investment_query, {
                "name": investor["investor_name"],
                "company_name": company_dict.get("company_name", "Unknown"),
                "investment_amount": investment_amount
            })

    # Insert Market Segments
    market_segments = data.get("Market Segments", {}).get("market_segments", [])
    for segment in market_segments:
        if not segment:
            continue  # Skip empty values

        market_query = "MERGE (m:MarketSegment {name: $name})"
        db.run_query(market_query, {"name": segment})

        market_relation_query = """
        MATCH (c:Company {name: $company_name})
        MATCH (m:MarketSegment {name: $name})
        MERGE (c)-[:TARGETS]->(m)
        """
        db.run_query(market_relation_query, {
            "company_name": company_dict.get("company_name", "Unknown"),
            "name": segment
        })

    # Insert Customers & Customer Relationships
    customers = data.get("Customers", {}).get("customers", [])
    for customer in customers:
        if not customer.get("customer_name"):
            continue  # Skip empty values

        # Ensure the customer company node exists
        customer_query = "MERGE (cust:Company {name: $name})"
        db.run_query(customer_query, {"name": customer["customer_name"]})

        # Create the CUSTOMER_OF relationship
        product_or_service = customer.get("product_or_service")
        if product_or_service is None or product_or_service == "":
            # Create relationship without the product_or_service property if it's null
            customer_relation_query = """
            MATCH (c:Company {name: $company_name})
            MATCH (cust:Company {name: $customer_name})
            MERGE (cust)-[:CUSTOMER_OF]->(c)
            """
            db.run_query(customer_relation_query, {
                "company_name": company_dict.get("company_name", "Unknown"),
                "customer_name": customer["customer_name"]
            })
        else:
            # Include the product_or_service property when it's available
            customer_relation_query = """
            MATCH (c:Company {name: $company_name})
            MATCH (cust:Company {name: $customer_name})
            MERGE (cust)-[:CUSTOMER_OF {product_or_service: $product_or_service}]->(c)
            """
            db.run_query(customer_relation_query, {
                "company_name": company_dict.get("company_name", "Unknown"),
                "customer_name": customer["customer_name"],
                "product_or_service": product_or_service
            })

    # Insert Competitors & Competition Relationships
    competitors = data.get("Competitors", {}).get("competitors", [])
    for competitor in competitors:
        if not competitor.get("competitor_name"):
            continue  # Skip if competitor's name is missing

        competitor_query = "MERGE (comp:Company {name: $name})"
        db.run_query(competitor_query, {"name": competitor["competitor_name"]})

        # Handle null competitive_advantage values
        competitive_advantage = competitor.get("competitive_advantage")
        if competitive_advantage is None or competitive_advantage == "":
            # Create relationship without the competitive_advantage property if it's null
            competitor_relation_query = """
            MATCH (c:Company {name: $company_name})
            MATCH (comp:Company {name: $competitor_name})
            MERGE (c)-[:COMPETES_WITH]->(comp)
            """
            db.run_query(competitor_relation_query, {
                "company_name": company_dict.get("company_name", "Unknown"),
                "competitor_name": competitor["competitor_name"]
            })
        else:
            # Include the competitive_advantage property when it's available
            competitor_relation_query = """
            MATCH (c:Company {name: $company_name})
            MATCH (comp:Company {name: $competitor_name})
            MERGE (c)-[:COMPETES_WITH {competitive_advantage: $advantage}]->(comp)
            """
            db.run_query(competitor_relation_query, {
                "company_name": company_dict.get("company_name", "Unknown"),
                "competitor_name": competitor["competitor_name"],
                "advantage": competitive_advantage
            })

    # Insert Previous Companies & Work Relationships
    previous_companies = data.get("Previous Companies", {}).get("previous_companies", [])
    for prev_company in previous_companies:
        if not prev_company.get("individual_name") or not prev_company.get("company_name"):
            continue  # Skip if any required data is missing

        prev_company_query = "MERGE (pc:Company {name: $company})"
        db.run_query(prev_company_query, {"company": prev_company["company_name"]})

        # Handle null role values
        role = prev_company.get("role")
        if role is None or role == "":
            # Create relationship without the role property if it's null
            prev_work_relation_query = """
            MATCH (p:Person {name: $person})
            MATCH (pc:Company {name: $company})
            MERGE (p)-[:WORKED_AT]->(pc)
            """
            db.run_query(prev_work_relation_query, {
                "person": prev_company["individual_name"],
                "company": prev_company["company_name"]
            })
        else:
            # Include the role property when it's available
            prev_work_relation_query = """
            MATCH (p:Person {name: $person})
            MATCH (pc:Company {name: $company})
            MERGE (p)-[:WORKED_AT {role: $role}]->(pc)
            """
            db.run_query(prev_work_relation_query, {
                "person": prev_company["individual_name"],
                "company": prev_company["company_name"],
                "role": role
            })

    # Close the Database Connection
    db.close()

    print("Data successfully inserted into Neo4j!")

def process_company(company_name, pdf_path, website_url, neo4j_uri, neo4j_user, neo4j_password, category_hierarchy):
    """Process a single company with the given information."""
    print(f"\n{'='*50}")
    print(f"Processing company: {company_name}")
    print(f"{'='*50}")
    
    # Process the website and get the results
    try:
        # Update the PDF path for this specific company
        pdf_path = "company_details/" + pdf_path
        print(f"Using PDF file: {pdf_path}")
        
        # Process the website and PDF
        print(f"Processing website: {website_url}")
        results = process_website_with_prompts(website_url, pdf_path)
        data = json.loads(results)
        
        # Map market segments
        if "Market Segments" in data and "market_segments" in data["Market Segments"]:
            market_segments = data["Market Segments"]["market_segments"]
            mapped_segments = map_market_segments(market_segments, category_hierarchy)
            data["Market Segments"]["market_segments"] = mapped_segments
        
        # Load data into Neo4j if credentials are provided
        if neo4j_uri and neo4j_user and neo4j_password:
            try:
                load_data_into_neo4j(data, neo4j_uri, neo4j_user, neo4j_password)
            except Exception as e:
                print(f"Error connecting to Neo4j: {e}")
                print("Skipping Neo4j import for this company.")
        
        # Save the results to a file
        # Handle different data structures for company information
        company_info = data.get('Company', {})
        if isinstance(company_info, list) and company_info and isinstance(company_info[0], dict):
            result_company_name = company_info[0].get('company_name', company_name)
        else:
            result_company_name = company_info.get('company_name', company_name)
        
        with open(f"company_data/{result_company_name}.json", "w") as f:
            f.write(json.dumps(data, indent=4))
        
        print(f"Process completed for {company_name}. Results saved to company_data_{result_company_name}.json")
        return True
    except Exception as e:
        print(f"Error processing company {company_name}: {e}")
        return False

def main():
    # Load environment variables
    configure()
    
    # Define your category hierarchy for market segment mapping
    category_hierarchy = {
        "Energy": ["Electric Vehicle Charging Infrastructure", "Fusion", "GeoThermal", "Next Gen"],
        "Financial Services": ["Banking as a service", "Carbon Offset Trading Platforms", "Decentralized Finance", "NFTs"],
        "Healthcare": ["AI-powered Drug Discovery", "Anti-Aging", "Assistive Tech", "CRISPR Diagnostics", "Fertility Tech", "Gene Therapies", "Medical Exoskeletons and Prosthetics", "Medical Robotics", "Mental Health Tech", "Nanomedicine", "Neurotechnology", "Psychedelics", "Sleep Tech", "Spatial Biology", "VR Health", 'Biotechnology'],
        "Information Technology": ["AGI", "Code Completion", "Blockchain Gaming", "Cloud Gaming", "Cognitive Computing", "Computational Storage", "DevSecOps", "Digital Avatars", "Digital Twins", "GenAI", "High Performance Computing"],
        "B2B": [],
        "B2C": [],
        "Materials and Resources": ["Indoor Farming", "Reforestation"]
    }
    
    # Get Neo4j credentials once
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_user = os.getenv('NEO4J_USERNAME')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    # Ensure we have credentials before proceeding
    if not neo4j_user or not neo4j_password:
        print("Neo4j username and password are required. Please set NEO4J_USER and NEO4J_PASSWORD environment variables or provide them when prompted.")
        proceed = input("Do you want to continue without Neo4j? (y/n): ").lower().strip()
        if proceed != 'y':
            return
        neo4j_uri = neo4j_user = neo4j_password = None
    
    # Read the Excel file
    try:
        excel_path = "data.xlsx"
        df = pd.read_excel(excel_path)
        print(f"Found {len(df)} companies to process in {excel_path}")
        
        # Check required columns
        required_columns = ['company_name', 'pdf_file', 'website_url']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Error: Missing required columns in Excel file: {missing_columns}")
            print(f"Required columns are: {required_columns}")
            return
        
        # Process each company
        success_count = 0
        for index, row in df.iterrows():
            company_name = row['company_name']
            pdf_file = row['pdf_file']
            website_url = row['website_url']
            
            print(f"\nProcessing {index+1}/{len(df)}: {company_name}")
            
            # Process the company
            success = process_company(
                company_name, 
                pdf_file, 
                website_url, 
                neo4j_uri, 
                neo4j_user, 
                neo4j_password, 
                category_hierarchy
            )
            
            if success:
                success_count += 1
        
        # Print summary
        print(f"\nProcessing complete. Successfully processed {success_count}/{len(df)} companies.")
    
    except FileNotFoundError:
        print(f"Error: Excel file 'data.xlsx' not found. Please create this file with columns: company_name, pdf_file, website_url")
    except Exception as e:
        print(f"Error reading Excel file: {e}")

if __name__ == "__main__":
    main()