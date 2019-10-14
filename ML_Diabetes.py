from flask import Flask, flash, render_template, request, redirect, jsonify, url_for
from flask_mysqldb import MySQL
import numpy as np
import random
import pandas as pd
import sklearn
import plotly
import plotly.graph_objects as go
import chart_studio.plotly as py
import json
import joblib
import datetime as dt

app = Flask(__name__)


# MySQL configurations

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'nugroho21'
app.config['MYSQL_DB'] = 'hciproj'
app.config['MYSQL_HOST'] = 'localhost'
mysql = MySQL(app)

def get_user_credentials(username):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usercred WHERE username = '"+username+"';")
    data = cursor.fetchall()
    return data

def insert_user_credentials(username, password):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("insert into usercred values('"+username+"', '"+password+"');")
    conn.commit()
    print ('Added the user to the table.')

def insert_user_table(user_active):
    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute('''show tables''')
        key=cursor.fetchall()
        if user_active not in key:
            qry_table=f'''create table {user_active} (
                id int not null auto_increment,
                sugar int not null,
                measured varchar(100) not null,
                date_ varchar(100) not null,
                time_ varchar(100) not null,
                mood int not null,
                primary key(id));
            )'''
            cursor.execute(qry_table)
            print('user table inserted')
        else:
            print('table already exist')
    except conn.Error as error:
        print("Failed to insert into MySQL table {}".format(error))


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
       return render_template('index.html')
    if request.method == 'POST':
        username = request.form['username']
        storedusername = [i[0] for i in get_user_credentials(username)]
        password = request.form['password']
        storedpassword = [i[1] for i in get_user_credentials(username)]
        if username in storedusername and password in storedpassword:
            global user_active
            user_active=username
            print(user_active)
            insert_user_table(user_active)
            return redirect('predict')
        else:
            notice="Account not present"
            return render_template('index.html', notice=notice)

@app.route('/signup', methods=['POST'])
def signUp():
    username = request.form['username']
    storedusername=[i[0] for i in get_user_credentials(username)]
    password = request.form['password']
    if username not in storedusername:
        insert_user_credentials(username, password)
        # flash('User inserted')
        # return redirect(url_for('index'))
        result="User inserted"
    else:
        result='Username already used'
    return render_template('index.html', result=result)

# @app.route('/mainPage', methods=['GET', 'POST'])
# def mainPage():
#         return render_template('main.html')


@app.route('/predict', methods=['GET','POST'])
def predict():
    global user_active
    if request.method == 'GET':
        return render_template('main.html',user_active=user_active)
    if request.method == 'POST':
        if user_active!='':
            print(user_active)
            body=request.form
            Pregnancies = int(body['Pregnancies'])
            Glucose = int(body['Glucose'])
            BloodPressure = int(body['BloodPressure'])
            SkinThickness = int(body['SkinThickness'])
            Insulin =int (body['Insulin'])
            BMI = int(body['BMI'])
            DiabetesPedigreeFunction = int(body['DiabetesPedigreeFunction'])
            Age = int(body['Age'])
            
            pred=model.predict(scaler.transform([[
                Pregnancies,Glucose,BloodPressure,SkinThickness,Insulin,BMI,DiabetesPedigreeFunction,Age
            ]]))[0]
            if pred == 0 :
                result="You don't have diabetes"
            else :
                result="You may have diabetes"
            try : 
                conn = mysql.connection
                cursor = conn.cursor()
                qry_sugar='''insert into history (Nama, Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome) 
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ;'''
                recordTuple = (user_active, Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, pred) 
                cursor.execute(qry_sugar, recordTuple)
                conn.commit()
                print('record complete')
            except conn.Error as error:
                print('Failed to insert into MySQL table {}'.format(error))
            return render_template('main.html', result=result, show_result=True, user_active=user_active)
        else :
            msg="Please sign in first"
            return render_template('index.html', msg=msg)

@app.route('/signout')
def signout():
    global user_active
    user_active=''
    return redirect('/')

@app.route('/info')
def info():
    df_rate=pd.read_csv('number-of-deaths-by-risk-factor (1).csv')
    a=list(map(lambda s: s.replace('(deaths)' , ''), df_rate.columns.values))
    columns_={}
    for i in range(len(df_rate.columns.values)):
        columns_.update({df_rate.columns[i]:a[i]})
    dfnew=df_rate.rename(columns=columns_)
    dfnew.drop(['Entity','Code','Year'], axis=1,inplace=True)
    y=dfnew.columns.values
    x=dfnew[y].sum()
    sorty = [y for _,y in sorted(zip(x,y))]
    sortx = sorted(x)
    dfcolor=pd.read_csv('colors.csv', header=None)
    color=[]
    for i in range(len(y)):
        color.append(dfcolor[2][i])
    data =  go.Bar(
            x=sortx,
            y=sorty, 
            orientation='h',
            marker_color=color)
    data=[data]
    plotJson=json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('info.html', x=plotJson)    

@app.route('/diabetes_tracker', methods=['GET','POST'])
def diabetes_tracker():
    global user_active
    print(user_active)
    conn = mysql.connection
    cursor = conn.cursor()
    if request.method =='GET':
        cursor.execute(f'''select * from {user_active}''')
        key=cursor.fetchall()
        waktu=[x[3]+' '+x[4] for x in key]
        date=[dt.datetime.strptime(x[3], '%Y-%m-%d') for x in key]
        blod=[y[1] for y in key]
        print(date)
        print(blod)
        data =  [go.Scatter(x=date,y=blod)]
        layout = go.Layout(
            width=800,
            height=400,
            xaxis=go.layout.XAxis(
                title=go.layout.xaxis.Title(
                    text='Time',
                    font=dict(
                        family='Calibri',
                        size=18,
                        color='#7f7f7f'
                    )
                )
            ),
            yaxis=go.layout.YAxis(
                title=go.layout.yaxis.Title(
                    text='Blood Sugar Level mg/dl',
                    font=dict(
                        family='Calibri',
                        size=18,
                        color='#7f7f7f'
                    )
                )
            )
        )

        fig = dict(data=data, layout=layout)
        # Convert the figures to JSON
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template('track_2.html', user_active=user_active, x=graphJSON)
    if request.method =='POST':
        if user_active=='':
            # msg="Please sign in first"
            return redirect ('/')
        else :
            # ------------------ Record Data ------------------------

            body = request.form
            sugar_=str(body['sugar'])
            measured_=str(body['measured'])
            date_=str(body['date'])
            time_=str(body['time'])
            mood_=str(body['mood'])

            qry_sugar=f'''insert into {user_active} (sugar,measured,date_,time_, mood) values (%s,%s,%s,%s,%s)'''
            recordTuple = (sugar_,measured_,date_,time_, mood_) 
            cursor.execute(qry_sugar, recordTuple)
            conn.commit()
            result = 'record complete'
        # ------------------ Statistics ------------------------
            cursor.execute(f'''select * from {user_active}''')
            key=cursor.fetchall()
            waktu=[x[3]+' '+x[4] for x in key]
            # date=[dt.datetime.strptime(x, '%Y-%m-%d %H:%M') for x in waktu]
            date=[dt.datetime.strptime(x[3], '%Y-%m-%d') for x in key]
            blod=[y[1] for y in key]
            print(date)
            print(blod)
            data =  [go.Scatter(x=date,y=blod)]

            layout = go.Layout(
                width=800,
                height=400,
                xaxis=go.layout.XAxis(
                    title=go.layout.xaxis.Title(
                        text='Time',
                        font=dict(
                            family='Calibri',
                            size=18,
                            color='#7f7f7f'
                        )
                    )
                ),
                yaxis=go.layout.YAxis(
                    title=go.layout.yaxis.Title(
                        text='Blood Sugar Level mg/dl',
                        font=dict(
                            family='Calibri',
                            size=18,
                            color='#7f7f7f'
                        )
                    )
                )
            )
        
            fig = dict(data=data, layout=layout)
            # Convert the figures to JSON
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

            # except conn.Error as error:
            #     result = 'Failed to insert into MySQL table {}'.format(error)
            return render_template('track_2.html', user_active=user_active, result=result, x=graphJSON)


if __name__ == '__main__':
    model=joblib.load('model')
    scaler=joblib.load('scaler')
    app.run(
        debug=True
    )
