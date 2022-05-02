import pytest
import pandas as pd
import numpy as np
from src.model_train.ContNetModel import extract_from_dict, imdb_rule_rating, ContNetModel

@pytest.mark.parametrize(
	('input_dict', 'input_key' ,'expected_val'),
	(
		({'color':'black', 'age':2, 10:1}, 'color', 'black'),
		({'color':'black', 'age':2, 10:1}, 'age', 2),
		({'color':'black', 'age':2, 10:1}, 10, 1),
		({'color':'black', 'age':2, 10:1}, 'rand', None),
		({'color':'black', 'age':2, 10:1, 'list':['action', 'drama']}, 'list', ['action', 'drama']),
	),
)
def test_dictionary_extraction(input_dict, input_key,  expected_val):
	assert(extract_from_dict(input_dict, input_key) == expected_val)



def test_imdb_rating():
	data = [[100, 8.0], [50, 6.5]]
	df = pd.DataFrame(data, columns = ['vote_count', 'vote_average'])
	normalized_score_df = imdb_rule_rating(df, df['vote_average'].mean(), 50)
	
	assert normalized_score_df.values.tolist() == [7.75, 6.875]


def test_preprocess_user():
	Model = ContNetModel(None)
	user_data = [[1, 'A', 4], [1, 'A', 5], [1, 'A', 3], [2, 'A', 4], [2, 'B', 3]]
	df = pd.DataFrame(user_data, columns = ['user_id', 'title', 'rating'])
	expected_df = pd.DataFrame({'user_id':[1,2,2],'title':['A','A','B'], 'rating':[4.0,4.0,3.0]})
	expected_df.set_index('user_id', inplace = True)

	assert expected_df.equals(Model.preprocess_user(df))



@pytest.mark.parametrize(
	('input_df', 'expected_df'),
	(
		(pd.DataFrame({'title':['BestMovie'],'info':[{'overview': 'good movie', 'genres': [{ 'name':'action'}, { 'name': 'drama'}],
					'production_companies': [{ 'name': 'SEbrothers'}, { 'name': 'CMU'}], 'vote_average':6.5, 'vote_count': 100}]}),
		pd.DataFrame({'title':['BestMovie'], 'genres': [['action', 'drama']], 'overview': ['good movie'],
			'production_companies': [['SEbrothers', 'CMU']], 'vote_average':[6.5], 'vote_count': [100.0]})),

		(pd.DataFrame({'title':['BestMovie'],'info':[{'overview': 'good movie', 'genres': [{ 'name':'action'}, { 'name': 'drama'}],
					'production_companies': None, 'vote_average':'6.5', 'vote_count': '100'}]}),
		pd.DataFrame({'title':['BestMovie'], 'genres': [['action', 'drama']], 'overview': ['good movie'],
			'production_companies': [[]], 'vote_average':[6.5], 'vote_count': [100.0]})),
	)

)
def test_preprocess_movie(input_df, expected_df):
	Model = ContNetModel(None)
	assert expected_df.equals(Model.preprocess_movie(input_df))

def test_create_content():
	Model = ContNetModel(None)
	df = pd.DataFrame({'title':['BestMovie'], 'genres': [['action', 'drama']], 'overview': ['good movie'],
			'production_companies': [['SEbrothers', 'CMU']], 'vote_average':[6.5], 'vote_count': [100.0]})
	content_df = Model.create_content(df)

	expected_df = pd.DataFrame({'title':['BestMovie'], 'genres': ['action drama'], 'overview': ['good movie'],
			'production_companies': ['SEbrothers CMU'], 'vote_average':[6.5], 'vote_count': [100.0],
			'description':['good movie action drama action drama SEbrothers CMU SEbrothers CMU']})

	assert expected_df.equals(content_df)



def test_fetch_top_user_movies():
	
	user_data = [[1, 'MenInBlack1', 5], [1, 'MenInBlack2', 4], [1, 'MenInBlack3', 5], [1, 'Fargo', 5],
	             [2, 'MenInBlack1', 3], [2, 'MenInBlack2', 3], [2, 'MenInBlack3', 5], [2, 'Matrix4', 1],
	             [3, 'MenInBlack1', 5], [3, 'ToyStory', 4],
	             [4, 'shrek', 2]]
	urd = pd.DataFrame(user_data, columns = ['user_id', 'title', 'rating'])
	urd.set_index('user_id', inplace = True)

	titles = pd.DataFrame({'title':['MenInBlack1', 'MenInBlack2', 'MenInBlack3']})['title']
	
	best_movie_df = pd.DataFrame({'title':['MenInBlack1', 'MenInBlack2', 'MenInBlack3', 'shrek'],
		'genres': ['action drama', 'action', 'action thriller', 'comedy'],
		'overview': ['good movie', 'better movie', 'best movie', 'big green dude'],
		'production_companies': ['SEbrothers CMU', 'SEbrothers CMU', 'SEbrothers CMU', 'Diseny'],
		'vote_average':[6.5, 6.0, 7.0, 7.0], 'vote_count': [100.0, 110.0, 200.0, 170.0],
		'description':['good movie action drama action drama SEbrothers CMU SEbrothers CMU',
		'good movie action drama action drama SEbrothers CMU SEbrothers CMU',
		'good movie action drama action drama SEbrothers CMU SEbrothers CMU',
		'big green dude comedy comedy Diseny Diseny']})

	Model = ContNetModel(None)
	
	assert Model.get_top_user_movies(4, urd, titles, best_movie_df) == []
	assert Model.get_top_user_movies(3, urd, titles, best_movie_df) == ['MenInBlack1']
	assert Model.get_top_user_movies(2, urd, titles, best_movie_df) == ['MenInBlack1', 'MenInBlack2', 'MenInBlack3']
	assert Model.get_top_user_movies(1, urd, titles, best_movie_df) == ['MenInBlack1', 'MenInBlack2', 'MenInBlack3']


def test_get_recommend():
	titles = pd.DataFrame({'title':['MenInBlack1', 'MenInBlack2', 'MenInBlack3', 'shrek', 'Fargo']})['title']

	best_movie_df = pd.DataFrame({'title':['MenInBlack1', 'MenInBlack2', 'MenInBlack3', 'shrek'],
		'genres': ['action drama', 'action', 'action thriller', 'comedy'],
		'overview': ['good movie', 'better movie', 'best movie', 'big green dude'],
		'production_companies': ['SEbrothers CMU', 'SEbrothers CMU', 'SEbrothers CMU', 'Diseny'],
		'vote_average':[6.5, 6.0, 7.0, 7.0], 'vote_count': [100.0, 110.0, 200.0, 170.0],
		'description':['good movie action drama action drama SEbrothers CMU SEbrothers CMU',
		'good movie action drama action drama SEbrothers CMU SEbrothers CMU',
		'good movie action drama action drama SEbrothers CMU SEbrothers CMU',
		'big green dude comedy comedy Diseny Diseny']})

	indices = pd.Series(best_movie_df.index, index=best_movie_df['title'])
	cosine_sim = np. array([[1.0,    0.002, 0.003, 0.001],
						    [0.002,  1.0,   0.02,  0.001],
						    [0.003,  0.002, 1.0,   0.002],
						    [0.001,  0.001, 0.002, 1.0]]).reshape(4,4)


	Model = ContNetModel(None)
	assert  Model.get_recommendations('MenInBlack1', 2, indices, titles, cosine_sim) == ['MenInBlack3', 'MenInBlack2']
	assert  Model.get_recommendations('shrek', 1, indices, titles, cosine_sim) == ['MenInBlack3']