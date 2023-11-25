from flask import Flask, render_template, request
from pymongo import MongoClient
import pandas as pd
from flask import redirect, url_for


app = Flask(__name__)

# Connect to MongoDB
try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client["NoSQL_JComp"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Load datasets from CSV files
csv_file1_path = "MedsData1.csv"
csv_file2_path = "MedsData2.csv"
try:
    collection1_data = pd.read_csv(csv_file1_path)
    collection2_data = pd.read_csv(csv_file2_path)
except Exception as e:
    print(f"Error loading CSV files: {e}")

# Insert the data into MongoDB collections
try:
    db.collection1.insert_many(collection1_data.to_dict(orient='records'))
    db.collection2.insert_many(collection2_data.to_dict(orient='records'))
except Exception as e:
    print(f"Error inserting data into MongoDB: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        medicine_name = request.form['medicine_name']

        # Search for medicine in both datasets using MongoDB
        result_collection1 = list(db.collection1.find({"name": {"$regex": f".*{medicine_name}.*", "$options": "i"}}))
        result_collection2 = list(db.collection2.find({"product_name": {"$regex": f".*{medicine_name}.*", "$options": "i"}}))

        # Get some statistics
        stats_collection1 = get_statistics(collection1_data, 'price', 'is_discontinued')
        stats_collection2 = get_statistics(collection2_data, 'product_price')

        return render_template('result.html', result_collection1=result_collection1, result_collection2=result_collection2,
                               stats_collection1=stats_collection1, stats_collection2=stats_collection2)
    except Exception as e:
        print(f"Error in search: {e}")
        return render_template('error.html', error_message="An error occurred during the search.")

def get_statistics(data, price_column, discontinued_column=None):
    statistics = {
        'average_price': data[price_column].mean(),
        'median_price': data[price_column].median(),
        'max_price': data[price_column].max(),
        'min_price': data[price_column].min(),
    }

    if discontinued_column:
        statistics['num_discontinued'] = data[data[discontinued_column]].shape[0] if discontinued_column in data.columns else 0

    return statistics


@app.errorhandler(500)
def internal_server_error(e):
    error_message = "Internal Server Error. Please try again later."
    return render_template('error.html', error_message=error_message), 500

@app.route('/statistics')
def statistics():
    try:
        # Get overall statistics directly from MongoDB
        total_medicines_collection1 = db.collection1.count_documents({})
        total_medicines_collection2 = db.collection2.count_documents({})
        
        unique_medicines_collection1 = db.collection1.distinct("name")
        unique_medicines_collection2 = db.collection2.distinct("product_name")

        common_medicines = len(set(unique_medicines_collection1).intersection(unique_medicines_collection2))

        overall_stats = {
            'total_medicines_collection1': total_medicines_collection1,
            'total_medicines_collection2': total_medicines_collection2,
            'unique_medicines_collection1': len(unique_medicines_collection1),
            'unique_medicines_collection2': len(unique_medicines_collection2),
            'common_medicines': common_medicines,
        }

        # Get type distribution directly from MongoDB
        type_distribution_collection1 = db.collection1.aggregate([
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ])
        type_distribution_collection1 = {doc['_id']: doc['count'] for doc in type_distribution_collection1}

        type_distribution_collection2 = db.collection2.aggregate([
            {"$group": {"_id": "$sub_category", "count": {"$sum": 1}}}
        ])
        type_distribution_collection2 = {doc['_id']: doc['count'] for doc in type_distribution_collection2}

        # Get manufacturer distribution directly from MongoDB
        manufacturer_distribution_collection1 = db.collection1.aggregate([
            {"$group": {"_id": "$manufacturer_name", "count": {"$sum": 1}}}
        ])
        manufacturer_distribution_collection1 = {doc['_id']: doc['count'] for doc in manufacturer_distribution_collection1}

        manufacturer_distribution_collection2 = db.collection2.aggregate([
            {"$group": {"_id": "$product_manufactured", "count": {"$sum": 1}}}
        ])
        manufacturer_distribution_collection2 = {doc['_id']: doc['count'] for doc in manufacturer_distribution_collection2}

        # Prepare data for charts
        chart_data = {
            'labels_collection1': list(type_distribution_collection1.keys()),
            'data_collection1': list(type_distribution_collection1.values()),
            'labels_collection2': list(type_distribution_collection2.keys()),
            'data_collection2': list(type_distribution_collection2.values()),
        }

        return render_template('statistics.html', overall_stats=overall_stats, 
                               manufacturer_distribution_collection1=manufacturer_distribution_collection1,
                               manufacturer_distribution_collection2=manufacturer_distribution_collection2, 
                               chart_data=chart_data)
    except Exception as e:
        print(f"Error in statistics: {e}")

@app.route('/redirect_index')
def redirect_index():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
