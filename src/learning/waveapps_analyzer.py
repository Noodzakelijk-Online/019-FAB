import requests
from typing import Dict, Any, List

class WaveappsAnalyzer:
    """Analyzes existing Waveapps data to learn categorization patterns."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.access_token = self.config.get("waveapps_business_access_token") # Can be business or personal
        self.business_id = self.config.get("waveapps_business_id") # Can be business or personal
        self.api_url = "https://gql.waveapps.com/graphql/v1alpha"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def analyze_transactions(self) -> List[Dict[str, Any]]:
        """Fetches and analyzes transactions from Waveapps."""
        if not self.access_token or not self.business_id:
            print("Waveapps credentials not configured for analyzer.")
            return []

        # GraphQL query to fetch expenses. This is a simplified query.
        # In a real scenario, you'd paginate and fetch more details.
        query = f"""
            query {{ 
                business(id: \"{self.business_id}\") {{ 
                    expenses(first: 50) {{ # Fetching first 50 expenses
                        edges {{ 
                            node {{ 
                                id
                                description
                                amount {{ value currency }}
                                incurredAt
                                category {{ name }}
                                vendor {{ name }}
                            }}
                        }}
                    }}
                }}
            }}
        """

        try:
            response = requests.post(self.api_url, headers=self.headers, json={
                "query": query
            })
            response.raise_for_status()
            result = response.json()

            expenses = []
            edges = result.get("data", {}).get("business", {}).get("expenses", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                expenses.append({
                    "id": node.get("id"),
                    "description": node.get("description"),
                    "amount": node.get("amount", {}).get("value"),
                    "currency": node.get("amount", {}).get("currency"),
                    "date": node.get("incurredAt"),
                    "category": node.get("category", {}).get("name"),
                    "vendor": node.get("vendor", {}).get("name")
                })
            return expenses

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Waveapps transactions: {e}")
            return []

    def learn_patterns(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes transactions to extract categorization patterns."""
        vendor_category_map = {}
        description_keywords = {}
        
        for tx in transactions:
            vendor = tx.get("vendor")
            category = tx.get("category")
            description = tx.get("description", "").lower()

            if vendor and category:
                if vendor not in vendor_category_map:
                    vendor_category_map[vendor] = {}
                vendor_category_map[vendor][category] = vendor_category_map[vendor].get(category, 0) + 1
            
            # Simple keyword extraction from description
            for word in description.split():
                if len(word) > 3 and word.isalpha(): # Filter short words and non-alpha
                    if word not in description_keywords:
                        description_keywords[word] = {}
                    description_keywords[word][category] = description_keywords[word].get(category, 0) + 1

        # Convert counts to most frequent category
        final_vendor_map = {v: max(cats, key=cats.get) for v, cats in vendor_category_map.items()}
        final_keyword_map = {k: max(cats, key=cats.get) for k, cats in description_keywords.items()}

        return {
            "vendor_category_map": final_vendor_map,
            "description_keywords_map": final_keyword_map
        }


