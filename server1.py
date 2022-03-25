import numpy as np
import pandas as pd
from flask import Flask, request, Response, jsonify
from flask_cors import CORS, cross_origin
import os
import pymongo
# import faiss
from threading import Thread
# from sklearn.preprocessing import MinMaxScaler
from typing import Dict, List
import requests
from bson.json_util import dumps
import config
import sys

client = None
docs = None
# scaler = MinMaxScaler(feature_range=(0,1))
app = Flask(__name__, static_folder='./build', static_url_path='/')
# cors = CORS(app, resources={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'
df = None
restricted_column_list = ['glove_embedding', 'specter_embedding']
query_index = {
    "glove_embedding": None,
    "specter_embedding": None
}

topic_df = None

#newly add
def get_topics_by_topics(df, topic_ids, limit):
  total_x = 0
  total_y = 0
  for t in topic_ids:
    x = df['Coordinates'].loc[df['Topic ID'] == t].iloc[0][0]
    y = df['Coordinates'].loc[df['Topic ID'] == t].iloc[0][1]
    total_x = total_x + x
    total_y = total_y + y
  pos_x = total_x/len(topic_ids)
  pos_y = total_y/len(topic_ids)

  dist_dict = {}
  for index, row in df.iterrows():
    x = row['Coordinates'][0]
    y = row['Coordinates'][1]
    d = math.sqrt((x - pos_x)**2 + (y - pos_y)**2)
    dist_dict[row['Topic ID']] = d

  dist_dict_sort = sorted(dist_dict.items(), key=lambda x: x[1])
  topic_list = []

  for i in range(0,limit):
    topic_list.append(dist_dict_sort[i][0])

  return topic_list


# @app.route('/getPapers', methods = ['GET'])
# @cross_origin()
# def get_papers():
#     global df
#     response = df.loc[:, ~df.columns.isin(restricted_column_list)].to_json(orient="records", default_handler=str)
#     return Response(response)

#newly add
def load_topic_data():
    global client, docs, topic_df

    if config.data_source == "json":
        json_data = pd.read_json(config.raw_topicmodelling_json_datafile, orient="records")
        topic_df_data = pd.DataFrame(json_data)
        # df_data.dropna(subset=['Title', "Authors"], inplace=True)

    else:
        print("invalid config.data_source. Valid values are 'json', 'mongodb'")
        sys.exit()

    topic_df = topic_df_data

#newly add
@app.route('/getTopics', methods = ['GET'])
@cross_origin()
def get_topics():
    global topic_df
    response = topic_df.to_json(orient="records", default_handler=str)
    return Response(response)


#newly add
@app.route('/getSimilarTopicByTopic', methods=['POST'])
@cross_origin()
def get_similar_topics_by_topics():
    global topic_df
    input_payload = request.json
    input_type = input_payload["input_type"]
    if input_type == "Keyword":
        topic_words = input_payload["input_data"]
        topic_ids = list(topic_df[topic_df["Key Words"].isin(topic_words)]["Topic ID"]) #todo
    elif input_type == "ID":
        topic_ids = input_payload["input_data"]
    else:
        return Response("Valid input_type = Keyword / ID")

    limit = int(input_payload["limit"])

    # send limit*2? todo

    results_df = get_topics_by_topics(topic_df, topic_ids, limit)
    if results_df is None:
        return Response("[]")
    else:
        # apply the original limit to the final df
        return Response(results_df.head(limit).to_json(orient="records", default_handler=str))

@app.route('/')
@cross_origin()
def index():
    return app.send_static_file('index.html')


def load_data_and_create_index():
    # load_data()
    load_topic_data()
    # create_query_index()


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 3000))

    # This thread was added so that Heroku can run Flask and bind the $PORT ASAP. If it is unable to do that within 30 seconds, it will timeout.
    # Our process takes much longer than that so we start a new thread for it.
    Thread(target=load_data_and_create_index).start()

    app.run(host='0.0.0.0', port=port)  # Run it, baby!
