import json
import pandas as pd
from typing import Dict, List, Union
import logging

class DataConverter:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def read_json(self, input_file: str) -> Union[Dict, List]:
        """Read JSON data from file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading JSON: {str(e)}")
            raise

    def flatten_data(self, data: Union[Dict, List]) -> List[Dict]:
        """Flatten nested JSON data structure for DataFrame"""
        flattened = []
        
        # Handle list at root level
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Process each field in the dictionary
                    row = {
                        'source_file': item.get('source_file', ''),
                        'text': '',
                        'links': '',
                        'html': ''
                    }
                    # Process the actual content fields
                    for key, value in item.items():
                        if isinstance(value, list):
                            # If value is a list (like publications), process each item
                            for list_item in value:
                                if isinstance(list_item, dict):
                                    flattened.append({
                                        'source_file': item.get('source_file', ''),
                                        'field_name': key,
                                        'text': list_item.get('text', ''),
                                        'links': ', '.join(list_item.get('links', [])),
                                        'html': list_item.get('html', '')
                                    })
                        else:
                            # Handle non-list values
                            if key != 'source_file':  # Skip source_file as it's already included
                                row['field_name'] = key
                                row['text'] = str(value)
                                flattened.append(row.copy())
                                
        # Handle dictionary at root level
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            flattened.append({
                                'source_file': '',
                                'field_name': key,
                                'text': item.get('text', ''),
                                'links': ', '.join(item.get('links', [])),
                                'html': item.get('html', '')
                            })
                else:
                    flattened.append({
                        'source_file': '',
                        'field_name': key,
                        'text': str(value),
                        'links': '',
                        'html': ''
                    })
                    
        return flattened

    def convert_to_excel(self, data: List[Dict], output_file: str):
        """Convert data to Excel file"""
        try:
            df = pd.DataFrame(data)
            
            # Write to Excel
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Data']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 100)

            self.logger.info(f"Excel file created: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error creating Excel file: {str(e)}")
            raise

    def convert_to_csv(self, data: List[Dict], output_file: str):
        """Convert data to CSV file"""
        try:
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False, encoding='utf-8')
            self.logger.info(f"CSV file created: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error creating CSV file: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    converter = DataConverter()
    
    # Read JSON file
    json_data = converter.read_json('parsed_data.json')
    
    # Flatten the data
    flattened_data = converter.flatten_data(json_data)
    
    # Convert to both formats
    converter.convert_to_excel(flattened_data, 'output.xlsx')
    converter.convert_to_csv(flattened_data, 'output.csv')