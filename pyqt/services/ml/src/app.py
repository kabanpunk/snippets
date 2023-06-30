from fastapi import FastAPI
import numpy as np
import joblib
import psycopg2
import pandas as pd
import os

app = FastAPI()

# Loads
folder_path = '/app/src/model_files/'
y_scaler = joblib.load(folder_path + 'y_scaler.save')
advertisible_apps = np.load(folder_path + 'advertisible_apps.npy') 

DATABASE_URL = os.environ.get("DATABASE_URL")
try:
    conn = psycopg2.connect(DATABASE_URL)
except:
    pass


@app.get("/")
async def root():
    return {"message": "it works"}


@app.get("/predict/{user_id}")
async def predict(user_id: int):
    users = pd.DataFrame.from_dict({1 : [0.59911674, 0.5094694, 0.49222076, 0.3755188, 0.45292872, 0.639894, 0.5422847, 0.3044214],
                                    2 : [0.5413608, 0.45819056, 0.5450425, 0.5425811, 0.49683744, 0.37575236, 0.37054804, 0.37528896]}, 
                                orient='index')

    user_vector = users.loc[user_id].to_numpy()

    idx = np.random.randint(0, advertisible_apps.shape[0])
    pred = advertisible_apps[idx]

    OUTPUT_SIZE = 5
    def find_nearest_apps(target, advertisible_apps=advertisible_apps):

        def euc_dist_onedim(y_true, y_pred):
            return np.sqrt(np.sum(np.square(y_true - y_pred)))

        output = np.zeros((OUTPUT_SIZE,), dtype=int)
        ds = np.full((OUTPUT_SIZE,), 1e4)
        max_d = ds.max()

        for idx, app in enumerate(advertisible_apps):

            latent = app

            d = float(euc_dist_onedim(target, latent))

            if d < max_d:

                for i in range(output.size):
                    if d < ds[i]:
                        ds[i] = d
                        output[i] = idx
                        max_d = ds.max()
                        break
        
        return output
    nearest_apps = find_nearest_apps(pred)
    output = list(nearest_apps)


    try:
        return {'prediction': str(output)}
    except TypeError as e:
        return {'error': str(e)}
