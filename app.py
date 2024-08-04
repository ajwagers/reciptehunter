from flask import Flask, request, render_template_string, session, jsonify
import requests
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import json
import os

app = Flask(__name__)

def load_api_key(env_path: Path) -> str:
    with open(env_path) as f:
        for line in f:
            if line.startswith('API_KEY'):
                return line.strip().split('=')[-1]
    raise ValueError("API_KEY not found in .env file")

def search_recipes(ingredients: List[str], avoid: List[str], diet: List[str], intolerances: List[str], api_key: str) -> List[Dict]:
    params = {
        'apiKey': api_key,
        'number': 10,  # Limit to 10 results
        'addRecipeInformation': True,  # This will include the summary in the response
    }
    
    if ingredients:
        params['includeIngredients'] = ','.join(ingredients)
    if avoid:
        params['excludeIngredients'] = ','.join(avoid)
    if diet:
        params['diet'] = ','.join(diet)
    if intolerances:
        params['intolerances'] = ','.join(intolerances)
    
    api_url = 'https://api.spoonacular.com/recipes/complexSearch'
    
    res = requests.get(api_url, params=params)
    res.raise_for_status()
    data = res.json()
    
    # Filter out recipes with avoided ingredients
    filtered_results = []
    for recipe in data.get('results', []):
        if not any(ingredient.lower() in recipe['title'].lower() for ingredient in avoid):
            filtered_results.append(recipe)
    
    return filtered_results

def get_recipe_details(recipe_id: int, api_key: str) -> Dict:
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {'apiKey': api_key}
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json()

def get_recipe_summary(recipe_id: int, api_key: str) -> str:
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/summary"
    params = {'apiKey': api_key}
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json()['summary']

def load_saved_searches():
    saved_searches_path = Path(__file__).parent / 'saved_searches.json'
    if saved_searches_path.exists():
        with open(saved_searches_path, 'r') as f:
            return json.load(f)
    return {}

def save_searches(searches):
    saved_searches_path = Path(__file__).parent / 'saved_searches.json'
    with open(saved_searches_path, 'w') as f:
        json.dump(searches, f)

# Load API key
env_path = Path(__file__).parent / 'recipehunter.env'
API_KEY = load_api_key(env_path)
#app.secret_key = load_api_key(env_path)

# Predefined lists
POPULAR_INGREDIENTS = [
    "Chicken", "Beef", "Pork", "Pasta", "Rice", "Potatoes", "Onions", "Garlic",
    "Tomatoes", "Cheese", "Eggs", "Milk", "Bread", "Butter", "Olive Oil",
    "Salt", "Pepper", "Sugar", "Flour", "Carrots", "Celery", "Bell Peppers",
    "Broccoli", "Spinach", "Lettuce", "Corn", "Beans", "Mushrooms", "Lemon", "Lime"
]

DIET_OPTIONS = [
    "Gluten Free", "Ketogenic", "Vegetarian", "Lacto-Vegetarian", "Ovo-Vegetarian",
    "Pescetarian", "Paleo", "Primal", "Low FODMAP", "Whole30"
]

INTOLERANCE_OPTIONS = [
    "Dairy", "Egg", "Gluten", "Grain", "Peanut", "Seafood", "Sesame", "Shellfish",
    "Soy", "Sulfite", "Tree Nut", "Wheat"
]

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recipe Hunter</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            transition: background-color 0.3s, color 0.3s;
            background-color: #333;
            color: #f4f4f4;
        }
        body.light-mode {
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: auto;
            display: flex;
        }
        .search-section {
            flex: 1;
            padding-right: 20px;
        }
        .results-section {
            flex: 1;
            padding-left: 20px;
        }
        h1, h2 {
            color: #f4f4f4;
        }
        .light-mode h1, .light-mode h2 {
            color: #333;
        }
        select, input[type="submit"] {
            margin-bottom: 10px;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            margin-bottom: 15px;
            background-color: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 5px;
        }
        .light-mode li {
            background-color: rgba(0, 0, 0, 0.05);
        }
        .error {
            color: #ff6b6b;
            font-weight: bold;
        }
        .mode-toggle {
            position: fixed;
            top: 10px;
            right: 10px;
        }
        .select2-container--default .select2-selection--multiple,
        .select2-container--default .select2-selection--single {
            background-color: #444;
            border: 1px solid #fff;
            color: #f4f4f4;
        }
        .select2-container--default .select2-selection--multiple .select2-selection__choice {
            background-color: #555;
            color: #f4f4f4;
            border: 1px solid #777;
        }
        .select2-container--default .select2-results__option {
            background-color: #444;
            color: #f4f4f4;
        }
        .select2-container--default .select2-results__option--highlighted[aria-selected] {
            background-color: #555;
        }
        .light-mode .select2-container--default .select2-selection--multiple,
        .light-mode .select2-container--default .select2-selection--single {
            background-color: #fff;
            border: 1px solid #aaa;
            color: #333;
        }
        .light-mode .select2-container--default .select2-selection--multiple .select2-selection__choice {
            background-color: #e4e4e4;
            color: #333;
            border: 1px solid #aaa;
        }
        .light-mode .select2-container--default .select2-results__option {
            background-color: #fff;
            color: #333;
        }
        .light-mode .select2-container--default .select2-results__option--highlighted[aria-selected] {
            background-color: #ddd;
        }
        .recipe-summary {
            font-style: italic;
            margin-top: 5px;
        }
        #search-name {
            width: 100%;
            padding: 5px;
            margin-bottom: 10px;
        }
        #save-search {
            margin-top: 10px;
        }
        #saved-searches-list {
            display: none;
            margin-top: 10px;
        }
        #saved-searches-list select {
            width: 100%;
            margin-bottom: 10px;
        }
    </style>
   <script>
        $(document).ready(function() {
            $('.select2-multi').select2({
                tags: true,
                tokenSeparators: [',', ' '],
                placeholder: "Select or type ingredients"
            });
            $('.select2-dropdown').select2({
                placeholder: "Select options"
            });
            
            // Mode toggle
            function setMode(mode) {
                if (mode === 'light') {
                    $('body').addClass('light-mode');
                    localStorage.setItem('mode', 'light');
                    $('#mode-toggle').prop('checked', false);
                } else {
                    $('body').removeClass('light-mode');
                    localStorage.setItem('mode', 'dark');
                    $('#mode-toggle').prop('checked', true);
                }
            }

            // Check localStorage for saved mode
            var savedMode = localStorage.getItem('mode') || 'dark';
            setMode(savedMode);

            // Mode toggle event listener
            $('#mode-toggle').change(function() {
                setMode(this.checked ? 'dark' : 'light');
            });

            // Clear All button
            $('#clear-all').click(function() {
                $('.select2-multi, .select2-dropdown').val(null).trigger('change');
                $('#search-name').val('');
                // Clear results section
                $('.results-section').html('');
                // Clear session data
                $.post('/clear_session');
                // Hide saved searches list if it's visible
                $('#saved-searches-list').hide();
            });

             // Save Search button
            $('#save-search').click(function() {
                var searchData = {
                    name: $('#search-name').val() || 'Unnamed Search',
                    ingredients: $('#ingredients').val(),
                    avoid: $('#avoid').val(),
                    diet: $('#diet').val(),
                    intolerances: $('#intolerances').val(),
                    recipes: []  // This will be populated with recipe data
                };

                // Collect recipe data
                $('.recipe-item').each(function() {
                    searchData.recipes.push({
                        title: $(this).find('.recipe-title').text(),
                        summary: $(this).find('.recipe-summary').text(),
                        id: $(this).data('recipe-id')
                    });
                });

                $.ajax({
                    url: '/save_search',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(searchData),
                    success: function(response) {
                        alert('Search saved successfully!');
                    },
                    error: function(error) {
                        alert('Error saving search: ' + error.responseText);
                    }
                });
            });
            // Load Saved Searches button
            $('#load-saved-searches').click(function() {
                $.get('/get_saved_searches', function(data) {
                    var selectHtml = '<select id="saved-search-select">';
                    for (var key in data) {
                        selectHtml += '<option value="' + key + '">' + key + '</option>';
                    }
                    selectHtml += '</select>';
                    $('#saved-searches-list').html(selectHtml + '<button id="load-selected-search">Load Selected Search</button>');
                    $('#saved-searches-list').show();
                });
            });

            // Load Selected Search button
            $(document).on('click', '#load-selected-search', function() {
                var selectedSearch = $('#saved-search-select').val();
                $.get('/load_saved_search/' + encodeURIComponent(selectedSearch), function(data) {
                    $('#search-name').val(selectedSearch);
                    $('#ingredients').val(data.ingredients).trigger('change');
                    $('#avoid').val(data.avoid).trigger('change');
                    $('#diet').val(data.diet).trigger('change');
                    $('#intolerances').val(data.intolerances).trigger('change');
                    alert('Search loaded successfully!');
                });
            });
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="search-section">
            <h1>Recipe Hunter</h1>
            <form method="post">
                <label for="search-name">Search Name:</label><br>
                <input type="text" id="search-name" name="search_name" value="{{ session.get('search_name', '') }}" placeholder="Enter a name for your search"><br>
                <label for="ingredients">Ingredients:</label><br>
                <select class="select2-multi" id="ingredients" name="ingredients" multiple="multiple" style="width: 100%;">
                    {% for ingredient in popular_ingredients %}
                        <option value="{{ ingredient }}" {% if ingredient in session.get('ingredients', []) %}selected{% endif %}>{{ ingredient }}</option>
                    {% endfor %}
                </select><br>
                <label for="avoid">Ingredients to avoid:</label><br>
                <select class="select2-multi" id="avoid" name="avoid" multiple="multiple" style="width: 100%;">
                    {% for ingredient in popular_ingredients %}
                        <option value="{{ ingredient }}" {% if ingredient in session.get('avoid', []) %}selected{% endif %}>{{ ingredient }}</option>
                    {% endfor %}
                </select><br>
                <label for="diet">Diet:</label><br>
                <select class="select2-dropdown" id="diet" name="diet" multiple="multiple" style="width: 100%;">
                    {% for diet in diet_options %}
                        <option value="{{ diet }}" {% if diet in session.get('diet', []) %}selected{% endif %}>{{ diet }}</option>
                    {% endfor %}
                </select><br>
                <label for="intolerances">Intolerances:</label><br>
                <select class="select2-dropdown" id="intolerances" name="intolerances" multiple="multiple" style="width: 100%;">
                    {% for intolerance in intolerance_options %}
                        <option value="{{ intolerance }}" {% if intolerance in session.get('intolerances', []) %}selected{% endif %}>{{ intolerance }}</option>
                    {% endfor %}
                </select><br>
                <input type="submit" value="Search Recipes">
                <button type="button" id="clear-all">Clear All</button>
                <button type="button" id="save-search">Save Search</button>
                <button type="button" id="load-saved-searches">Load Saved Searches</button>
            </form>
            <div id="saved-searches-list"></div>
        </div>
        <div class="results-section">
            {% if recipes is not none %}
                {% if recipes %}
                    <h2>Recipes:</h2>
                    <ul>
                    {% for recipe in recipes %}
                        <li class="recipe-item" data-recipe-id="{{ recipe.id }}">
                            <a href="{{ url_for('recipe_details', recipe_id=recipe.id) }}" class="recipe-title">{{ recipe.title }}</a>
                            <p class="recipe-summary">{{ recipe.summary[:120] }}...</p>
                        </li>
                    {% endfor %}
                    </ul>
                {% else %}
                    <p>No recipes found. Try adjusting your search criteria.</p>
                {% endif %}
            {% endif %}
            {% if error %}
                <p class="error">{{ error }}</p>
            {% endif %}
        </div>
    </div>
    <div class="mode-toggle">
        <label for="mode-toggle">Dark Mode</label>
        <input type="checkbox" id="mode-toggle">
    </div>
</body>
</html>
'''

@app.route('/save_search', methods=['POST'])
def save_search():
    search_data = request.json
    search_name = search_data.get('name') or f"New Search {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    saved_searches = load_saved_searches()
    saved_searches[search_name] = {
        'ingredients': search_data.get('ingredients', []),
        'avoid': search_data.get('avoid', []),
        'diet': search_data.get('diet', []),
        'intolerances': search_data.get('intolerances', []),
        'recipes': search_data.get('recipes', [])
    }
    save_searches(saved_searches)
    
    return jsonify({'message': 'Search saved successfully'}), 200

@app.route('/get_saved_searches', methods=['GET'])
def get_saved_searches():
    return jsonify(load_saved_searches())

@app.route('/load_saved_search/<search_name>')
def load_saved_search(search_name):
    saved_searches = load_saved_searches()
    if search_name in saved_searches:
        return jsonify(saved_searches[search_name])
    else:
        return jsonify({'error': 'Search not found'}), 404

@app.route('/clear_session', methods=['POST'])
def clear_session():
    # Clear everything from the session except saved searches
    for key in list(session.keys()):
        if key != 'saved_searches':
            session.pop(key)
    return '', 204

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        search_name = request.form.get('search_name') or f"New Search {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if not search_name:
            search_name = f"new search {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        app.secret_key = search_name  # Set the secret key dynamically
        
        ingredients = request.form.getlist('ingredients')
        avoid = request.form.getlist('avoid')
        diet = request.form.getlist('diet')
        intolerances = request.form.getlist('intolerances')
        
        # Store the form data in the session
        session['search_name'] = search_name
        session['ingredients'] = ingredients
        session['avoid'] = avoid
        session['diet'] = diet
        session['intolerances'] = intolerances
        
        try:
            recipes = search_recipes(ingredients, avoid, diet, intolerances, API_KEY)
            return render_template_string(HTML_TEMPLATE, 
                                          recipes=recipes, 
                                          popular_ingredients=POPULAR_INGREDIENTS,
                                          diet_options=DIET_OPTIONS,
                                          intolerance_options=INTOLERANCE_OPTIONS)
        except Exception as e:
            return render_template_string(HTML_TEMPLATE, 
                                          error=f"An error occurred: {str(e)}", 
                                          recipes=None,
                                          popular_ingredients=POPULAR_INGREDIENTS,
                                          diet_options=DIET_OPTIONS,
                                          intolerance_options=INTOLERANCE_OPTIONS)

    # Set a default secret key for GET requests
    app.secret_key = f"new search {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return render_template_string(HTML_TEMPLATE, 
                                  recipes=None,
                                  popular_ingredients=POPULAR_INGREDIENTS,
                                  diet_options=DIET_OPTIONS,
                                  intolerance_options=INTOLERANCE_OPTIONS)


@app.route('/recipe/<int:recipe_id>')
def recipe_details(recipe_id):
    try:
        details = get_recipe_details(recipe_id, API_KEY)
        summary = get_recipe_summary(recipe_id, API_KEY)
        
        ingredients_list = ''.join(f'<li>{item["original"]}</li>' for item in details['extendedIngredients'])
        
        recipe_html = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{details['title']} - Recipe Details</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    max-width: 800px;
                    margin: auto;
                    background-color: #333;
                    color: #f4f4f4;
                    transition: background-color 0.3s, color 0.3s;
                }}
                body.light-mode {{
                    background-color: #f4f4f4;
                    color: #333;
                }}
                h1, h2 {{
                    color: #f4f4f4;
                }}
                body.light-mode h1, body.light-mode h2 {{
                    color: #333;
                }}
                ul {{
                    padding-left: 20px;
                }}
                a {{
                    color: #4fc3f7;
                }}
                body.light-mode a {{
                    color: #1976d2;
                }}
                .top-bar {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background-color: #222;
                    padding: 10px;
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                }}
                body.light-mode .top-bar {{
                    background-color: #ddd;
                }}
                .back-button {{
                    margin-right: 20px;
                    padding: 5px 10px;
                    background-color: #4fc3f7;
                    color: #333;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                body.light-mode .back-button {{
                    background-color: #1976d2;
                    color: #fff;
                }}
                .content {{
                    margin-top: 60px;
                }}
            </style>
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <script>
                $(document).ready(function() {{
                    function setMode(mode) {{
                        if (mode === 'light') {{
                            $('body').addClass('light-mode');
                            localStorage.setItem('mode', 'light');
                            $('#mode-toggle').prop('checked', false);
                        }} else {{
                            $('body').removeClass('light-mode');
                            localStorage.setItem('mode', 'dark');
                            $('#mode-toggle').prop('checked', true);
                        }}
                    }}

                    var savedMode = localStorage.getItem('mode') || 'dark';
                    setMode(savedMode);

                    $('#mode-toggle').change(function() {{
                        setMode(this.checked ? 'dark' : 'light');
                    }});
                }});
            </script>
        </head>
        <body>
            <div class="top-bar">
                <a href="javascript:history.back()" class="back-button">Back to Search</a>
                <div class="mode-toggle">
                    <label for="mode-toggle">Dark Mode</label>
                    <input type="checkbox" id="mode-toggle">
                </div>
            </div>
            <div class="content">
                <h1>{details['title']}</h1>
                <h2>Ingredients:</h2>
                <ul>
                {ingredients_list}
                </ul>
                <h2>Summary:</h2>
                <p>{summary}</p>
                <h2>Instructions:</h2>
                <p>{details['instructions']}</p>
                <p><a href="{details['sourceUrl']}">Original Recipe</a></p>
            </div>
        </body>
        </html>
        '''
        
        return recipe_html
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Load API key
env_path = Path(__file__).parent / 'recipehunter.env'
try:
    app.config['API_KEY'] = load_api_key(env_path)
except Exception as e:
    print(f"Error loading API key: {e}")
    exit(1)

# Define constants
POPULAR_INGREDIENTS = [
    "Chicken", "Beef", "Pork", "Pasta", "Rice", "Potatoes", "Onions", "Garlic",
    "Tomatoes", "Cheese", "Eggs", "Milk", "Bread", "Butter", "Olive Oil",
    "Salt", "Pepper", "Sugar", "Flour", "Carrots", "Celery", "Bell Peppers",
    "Broccoli", "Spinach", "Lettuce", "Corn", "Beans", "Mushrooms", "Lemon", "Lime"
]

DIET_OPTIONS = [
    "Gluten Free", "Ketogenic", "Vegetarian", "Lacto-Vegetarian", "Ovo-Vegetarian",
    "Pescetarian", "Paleo", "Primal", "Low FODMAP", "Whole30"
]

INTOLERANCE_OPTIONS = [
    "Dairy", "Egg", "Gluten", "Grain", "Peanut", "Seafood", "Sesame", "Shellfish",
    "Soy", "Sulfite", "Tree Nut", "Wheat"
]


if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    app.run(debug=True)