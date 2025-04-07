# Market Mapping

Generate a market map for a list of companies. The code is in the `market_map.py` file

## Requirements

- A `data.xlsx` file with the following columns:
  - `Company Name`
  - `file_path` - file with company information. ( In this case, pitchbook profile)
  - `Company URL`
- A `company_details` directory with files for each company.
- A `.env` file with the following secrest
  - `GEMINI_API_KEY` - Gemini API key
  - `NEO4J_URL` - Neo4j URL
  - `NEO4J_USERNAME` - Neo4j username
  - `NEO4J_PASSWORD` - Neo4j password

## How does it work

- The script reads the `data.xlsx` file and extracts the company names, company URLs and file path.
- It scrapes the company website and saves it in temporary files
- It reads the file with company information
- It sends the details to the `Gemini` API, with a refined prompt and strict json format
- It saves the response to a file
- It saves the response to a neo4j database

# Market Reporting ( Work In Progress)

Automating market report

## Processing

- `tembo.py` file saves the file to database
- `data_processing.py` file generates the excel sheet, map and takeaaways
- `doc_generation.py` file generates the competitor market report

## Results

- `results.xlsx` - has median metrics for various rounds
- `map.html` - global map with location of competitors
- `Competitor_Analysis.docx` - AI generated word document with market report
