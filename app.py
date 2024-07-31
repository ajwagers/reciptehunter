from flask import Flask, request, render_template_string
import requests
from pathlib import Path
from typing import List, Dict

app = Flask(__name__)

def load_api_key(env_path: Path) -> str:
    with open(env_path) as f:
        for line in f:
            if line.startswith('API_KEY'):
                return line.strip().split('=')[-1]
    raise ValueError("API_KEY not found in .env file")

def search_recipes(ingredients: List[str], avoid: List[str], api_key: str) -> List[Dict]:
    ingr_str = '%2C'.join(ingredients)
    api_url = f'https://api.spoonacular.com/recipes/findByIngredients?ingredients={ingr_str}&apiKey={api_key}'
    
    res = requests.get(api_url)
    res.raise_for_status()
    data = res.json()
    
    return [recipe for recipe in data 
            if not any(avoid_ingr.lower() in str(recipe['missedIngredients']).lower() for avoid_ingr in avoid)]

def get_recipe_details(recipe_id: int, api_key: str) -> Dict:
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information?apiKey={api_key}"
    res = requests.get(url)
    res.raise_for_status()
    return res.json()

def get_recipe_summary(recipe_id: int, api_key: str) -> str:
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/summary?apiKey={api_key}"
    res = requests.get(url)
    res.raise_for_status()
    return res.json()['summary']

# Load API key
env_path = Path(__file__).parent / 'recipehunter.env'
API_KEY = load_api_key(env_path)

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Recipe Hunter</title>
</head>
<body>
    <h1>Recipe Hunter</h1>
    <form method="post">
        <label for="ingredients">Ingredients (comma-separated):</label><br>
        <input type="text" id="ingredients" name="ingredients" required><br>
        <label for="avoid">Ingredients to avoid (comma-separated):</label><br>
        <input type="text" id="avoid" name="avoid"><br>
        <input type="submit" value="Search Recipes">
    </form>
    {% if recipes %}
        <h2>Recipes:</h2>
        <ul>
        {% for recipe in recipes %}
            <li><a href="{{ url_for('recipe_details', recipe_id=recipe.id) }}">{{ recipe.title }}</a></li>
        {% endfor %}
        </ul>
    {% endif %}
    {% if error %}
        <p style="color: red;">{{ error }}</p>
    {% endif %}
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        ingredients = request.form['ingredients'].split(',')
        avoid = request.form['avoid'].split(',') if request.form['avoid'] else []
        
        try:
            recipes = search_recipes(ingredients, avoid, API_KEY)
            return render_template_string(HTML_TEMPLATE, recipes=recipes)
        except Exception as e:
            return render_template_string(HTML_TEMPLATE, error=str(e))
    
    return render_template_string(HTML_TEMPLATE)

@app.route('/recipe/<int:recipe_id>')
def recipe_details(recipe_id):
    try:
        details = get_recipe_details(recipe_id, API_KEY)
        summary = get_recipe_summary(recipe_id, API_KEY)
        
        recipe_html = f'''
        <h1>{details['title']}</h1>
        <h2>Ingredients:</h2>
        <ul>
        {''.join(f'<li>{item["original"]}</li>' for item in details['extendedIngredients'])}
        </ul>
        <h2>Summary:</h2>
        <p>{summary}</p>
        <h2>Instructions:</h2>
        <p>{details['instructions']}</p>
        <p><a href="{details['sourceUrl']}">Original Recipe</a></p>
        <p><a href="/">Back to Search</a></p>
        '''
        
        return recipe_html
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)