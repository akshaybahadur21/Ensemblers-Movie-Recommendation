<div align="center">

<p align="center"> <img src="https://github.com/cmu-seai/group-project-s22-ensemblers/blob/master/assets/ensemblers_img.png" height="400px"></p>


</div>


# Ensemblers 🎬

A movie recommendations engine for 17-445/645 Software Engineering for AI-Enabled Systems

## Description 🍿
In this project, you will implement, evaluate, operate, monitor, and evolve a recommendation service for a scenario of a movie streaming service. As in previous individual assignments, you work with a scenario of a streaming service with about 1 million customers and 27k movies (for comparison, Netflix has about 180 million subscribers and over 300 million estimated users worldwide and about 4000 movies or 13k titles worldwide)

## Implementation 👨‍🔬

### Data Generation

1) Developed three python files to generate data from the kafka stream, movie API and rating API respectively.
2) The generated data is stored in flat files for later consumption.

### Model Training

Models tried

1) KNN Collaborative Filtering 
2) Content-based Collaborative Filtering.

### MongoDB Schema
- Database name: `ensemblers_web`
- Collection name: `recommend`
- Document schema:
```python
{
  "_id": "1", # We replace the native _id field with user id
  "recommend": "1,2,3,4,5" # a string of comma-separated movie ids 
}
```

If you face any problem, kindly raise an issue

## Setup 🖥️

### Web server
1) Create a conda Python 3.8 environment for the web server.
2) Generate the flask server code according to our openapi specs: `./openapi/gen_api_layer.sh`.
3) Install web server dependencies: `pip install -r backend/src/gen/requirements.txt`
4) Prepare the .env file at `backend/src/impl/.env` if it doesn't exist.

## Execution 🐉
### Web server
1) Start development server: `./run_server.sh dev`
2) Start production server in the background: `nohup ./run_server.sh prod > server.log`

### MongoDB 
1) Delete and recreate the `recommend` collection:
```bash
mongo
use ensemblers_web
db.recommend.drop()
db.createCollection("recommend")
```

### Movie Recommendation Service

1) Install the requirements ```pip install requirements.txt -r```
2) Create an `application.properties` as per the user requirement
3) To run the application in background, ```nohup python3 MovieRecommendation.py application.properties > model.log & ```

## Results 📊

### Web server
1) A testable API UI page will be viewable on `localhost:8082/ui`.
<img src="https://github.com/cmu-seai/group-project-s22-ensemblers/blob/master/assets/postman.png">

## Team 🏆

- Aliakbar Izadkhah
- Akshay Bahadur
- Arpit Agrawal
- Chih-Hao (Oscar) Wang 
- Satish Channagiri Shreenivasa

## References 🔱
 
- The web server component reference the design and code in [ExplainaBoard](https://github.com/neulab/explainaboard_web) project, of which [Chih-Hao Wang](https://github.com/OscarWang114) is a contributor.
- [Recoomedation System Recitation from Spring 2020](https://github.com/ckaestne/seai/blob/S2020/recitations/06_Collaborative_Filtering.ipynb)
- [Introduction to Recommender System - Shuyu Luo](https://towardsdatascience.com/intro-to-recommender-system-collaborative-filtering-64a238194a26)
