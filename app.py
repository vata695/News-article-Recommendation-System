from flask import Flask, render_template, json, request, redirect, url_for
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
from flask import session
import nltk, re, pprint
from nltk.tag import pos_tag
from sklearn.feature_extraction.text import CountVectorizer
from sklearn import cluster
from sklearn.cluster import spectral_clustering
import random
import csv
mysql = MySQL()
app = Flask(__name__)



# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'news_articles'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

@app.route("/")
def main():
	return render_template('index.html')

@app.route("/showsignup")
def showsignup():
	return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
	username_form = request.form['inputUname1']
	email_form = request.form['inputEmail1']
	password_form = request.form['inputPassword1']
	confirm_password = request.form['inputConfirmPassword1']
	#return json.dumps({'status':'OK','user':username_form,'email':email_form,'password':password_form,'cpassword': confirm_password})	
	try:
		# validate the received values
		if username_form and email_form and password_form and confirm_password:
			conn = mysql.connect()
			cursor = conn.cursor()
			#hashed_password = generate_password_hash(password_form)
			cursor.execute("SELECT COUNT(1) FROM user WHERE emailid = %s", (email_form))
			if cursor.fetchone()[0]: 
				error1 = 'You\'re already registered. Please login!!'
				return render_template('signup.html',error=error1)
			else:
				if len(password_form) <= 8:
					error = 'Password too short!!'
					return render_template('signup.html',error=error)
				if password_form != confirm_password:
					error = 'Passwords don\'t match!!'
					return render_template('signup.html',error=error)
				else:
					cursor.callproc('sp_createUser',(username_form,email_form,confirm_password))
					conn.commit()
					cursor.callproc('sp_validateSignup',(email_form,))
					data=cursor.fetchall()
					if len(data) > 0:
						session['user']=data[0][0]						
					cursor.close()
					conn.close()
					return redirect(url_for('pref')) #preferences for later
		else:    	
			error = 'Please enter the required fields!!'
			return render_template('signup.html',error=error)
	except Exception as e:
		return json.dumps({'error':str(e)})


@app.route('/pref')
def pref():
	if 'user'in session:
		user_id=session['user']
	return render_template('pref.html')

@app.route('/preferences', methods=['POST'])
def preferences():
	if 'user'in session:
		user_id=session['user']
	conn=mysql.connect()
	cursor=conn.cursor()
	
	if request.form.get('national') is None:
		national_form=0
	else:
		national_form=1
		cursor.callproc('sp_enteruserpref',(user_id,national_form))
		conn.commit()

	if request.form.get('international') is None:
		international_form=0
	else:
		international_form=2
		cursor.callproc('sp_enteruserpref',(user_id,international_form))
		conn.commit()

	if request.form.get('business') is None:
		business_form=0
	else:
		business_form=3
		cursor.callproc('sp_enteruserpref',(user_id,business_form))
		conn.commit()

	if request.form.get('technology') is None:
		technology_form=0
	else:
		technology_form=4
		cursor.callproc('sp_enteruserpref',(user_id,technology_form))
		conn.commit()

	if request.form.get('lifestyle') is None:
		lifestyle_form=0
	else:
		lifestyle_form=5
		cursor.callproc('sp_enteruserpref',(user_id,lifestyle_form))
		conn.commit()

	if request.form.get('sports') is None:
		sports_form=0
	else:
		sports_form=6
		cursor.callproc('sp_enteruserpref',(user_id,sports_form))
		conn.commit()

	if request.form.get('entertainment') is None:
		entertainment_form=0
	else:
		entertainment_form=7
		cursor.callproc('sp_enteruserpref',(user_id,entertainment_form))
		conn.commit()
	
	conn.close()
	if national_form==0 and international_form==0 and business_form==0 and technology_form==0 and sports_form==0 and lifestyle_form==0 and entertainment_form==0 :
		error = 'Please choose your preferences'
		return render_template('pref.html',error=error)
		
	else:
		return redirect(url_for('showuserhome'))
		

@app.route('/login', methods=['POST'])
def login():    
	email_form = request.form['inputEmail2']
	password_form  = request.form['inputPassword2']
	if email_form and password_form:
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.callproc('sp_validateLogin',(email_form,)) # CHECKS IF EMAILID EXSIST
		data=cursor.fetchall()
		if len(data)>0:
			#if check_password_hash(str(data[0][3]),password_form):
			if str(data[0][3]) == password_form:
				session['user'] = data[0][0]
				user_id=session['user']
				uname=data[0][1]
				cursor.close()
				conn.close()
				return redirect(url_for('showuserhome'))#userhome for later
			else:
				cursor.close()
				conn.close()
				return render_template('signup.html',error = 'Wrong Password!!')
		else:
			cursor.close()
			conn.close()
			return render_template('signup.html',error = 'Please Register!!')			
	else:
		error = 'Please enter the required fields!!'
		return render_template('signup.html',error=error)

#declared as a global variable	
articles_dict=[]      
national_dict=[]
international_dict=[]
business_dict=[]
tech_dict=[]
lifest_dict=[]
sport_dict=[]
ent_dict=[]

non_genre_dict=[]
nnational_dict=[]
ninternational_dict=[]
nbusiness_dict=[]
ntech_dict=[]
nlifest_dict=[]
nsport_dict=[]
nent_dict=[]    
narticles_dict=[]

@app.route('/showuserhome')
def showuserhome():
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		cursor.callproc('sp_getArticles',(user_id,)) 
		articles=cursor.fetchall()
		
		for article in articles:
			article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
			if(article_dict['GenreId']==1):
				national_dict.append(article_dict)
			elif(article_dict['GenreId']==2):
				international_dict.append(article_dict)
			elif(article_dict['GenreId']==3):
				business_dict.append(article_dict)
			elif(article_dict['GenreId']==4):
				tech_dict.append(article_dict)
			elif(article_dict['GenreId']==5):
				lifest_dict.append(article_dict)
			elif(article_dict['GenreId']==6):
				sport_dict.append(article_dict)
			elif(article_dict['GenreId']==7):
				ent_dict.append(article_dict)
		articles_dict.append(national_dict)
		articles_dict.append(international_dict)
		articles_dict.append(business_dict)
		articles_dict.append(tech_dict)
		articles_dict.append(lifest_dict)
		articles_dict.append(sport_dict)
		articles_dict.append(ent_dict)
		
		cursor.callproc('sp_getGenre',(user_id,))
		genresobt=cursor.fetchall()
		total_genres=[1,2,3,4,5,6,7]

		genres=[]
		for i in range(len(genresobt)):
			genres.append(genresobt[i][0])

		non_pref_genres=[]
		for i in range(len(total_genres)):
			if total_genres[i] not in genres:
				non_pref_genres.append(total_genres[i])

		for ng in non_pref_genres:
			cursor.execute("SELECT * FROM articles WHERE date >=curdate()-1 AND genre_id = %s ORDER BY date DESC LIMIT 3",(ng,)) #doubtful
			narticles=cursor.fetchall()
			for narticle in narticles:
				narticle_dict={'ArticleId': narticle[0],'Headline':article[1], 'Date':narticle[3],'Summary':narticle[7],'Image':narticle[4] ,'GenreId': narticle[5],'Content':narticle[2],'Excited':narticle[8],'Happy':narticle[9],'Neutral':narticle[10],'Sad':narticle[11],'Morose':narticle[12]}
				if(narticle_dict['GenreId']==1):
					nnational_dict.append(narticle_dict)
				elif(narticle_dict['GenreId']==2):
					ninternational_dict.append(narticle_dict)
				elif(narticle_dict['GenreId']==3):
					nbusiness_dict.append(narticle_dict)
				elif(narticle_dict['GenreId']==4):
					ntech_dict.append(narticle_dict)
				elif(narticle_dict['GenreId']==5):
					nlifest_dict.append(narticle_dict)
				elif(narticle_dict['GenreId']==6):
					nsport_dict.append(narticle_dict)
				elif(narticle_dict['GenreId']==7):
					nent_dict.append(narticle_dict)
		narticles_dict.append(nnational_dict)
		narticles_dict.append(ninternational_dict)
		narticles_dict.append(nbusiness_dict)
		narticles_dict.append(ntech_dict)
		narticles_dict.append(nlifest_dict)
		narticles_dict.append(nsport_dict)
		narticles_dict.append(nent_dict)
		return render_template('userhome.html',username=str(uname),genres=genres,articles=articles_dict,glength=len(genres),nongenres=non_pref_genres,nglength=len(non_pref_genres),narticles=narticles_dict)
	else:
		return json.dumps({'html':'<span>Session error</span>'})

@app.route('/loadmore/<id>',methods=['GET'])
def loadmore(id):
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		load_genre=int(id)
		if load_genre == 1:
			genre='National'
		if load_genre == 2:
			genre='International'
		if load_genre == 3:
			genre='Business'
		if load_genre == 4:
			genre='Technology'
		if load_genre == 5:
			genre='Lifestyle'
		if load_genre == 6:
			genre='Sports'
		if load_genre == 7:
			genre='Entertainment'

		load_genre_articles=[]
		cursor.execute("SELECT * FROM articles WHERE date >=curdate()-1 AND genre_id = %s ORDER BY article_id DESC",(load_genre,)) #doubtful
		articles=cursor.fetchall()

		for article in articles:
			article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
			load_genre_articles.append(article_dict)
		x=len(load_genre_articles)
	return render_template('loadmore.html',username=str(uname),articles=load_genre_articles,genre=genre,length_genre=x)



@app.route('/articleview/<id>', methods=['GET'])
def articleview(id):
	#perform clustering here 
	article_id= id;
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]

		#generate article_id
		cursor.execute("SELECT * FROM articles WHERE article_id = %s", (id))
		news=cursor.fetchone()
		genre_ext=news[5]
		
		article_infodict={'ArticleNo':news[0],'Headline':news[1],'Summary':news[6],'Date':news[3],'Content':news[2],'Image':news[4],'GenreId':news[5],'Excited':news[8],'Happy':news[9],'Neutral':news[10],'Sad':news[11],'Morose':news[12]}
		
		#following filenames are specific to machine
		nat_filename = '/home/vaidehi/FlaskApp/cluster/national.csv'
		world_filename= '/home/vaidehi/FlaskApp/cluster/world.csv'
		business_filename= '/home/vaidehi/FlaskApp/cluster/world.csv'
		tech_filename= '/home/vaidehi/FlaskApp/cluster/tech.csv'
		life_filename='/home/vaidehi/FlaskApp/cluster/life.csv'
		sport_filename= '/home/vaidehi/FlaskApp/cluster/sports.csv'
		ent_filename= '/home/vaidehi/FlaskApp/cluster/entertainment.csv'

		clusters_list=[]

		
		if genre_ext == 1:
			with open(nat_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		elif genre_ext == 2:
			with open(world_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		elif genre_ext == 3:
			with open(business_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		elif genre_ext == 4:
			with open(tech_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		elif genre_ext == 5:
			with open(life_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		elif genre_ext == 6:
			with open(sport_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		elif genre_ext == 7:
			with open(ent_filename, 'r') as p:
				clusters_list = [list(map(int,rec)) for rec in csv.reader(p, delimiter=',')]
		
		
		desired_cluster=[]
		clusterid = 0
		ret_articles=[]
        #determine the cluster number
	
		
		flag = 0
		for i in range(0,len(clusters_list)):
			for j in range(0,len(clusters_list[i])):
				if int(article_id) == clusters_list[i][j]:
					clusterid=i						
					flag = 1
					break
				else:
					continue
			if(flag == 1):
				break

		for j in range(0,len(clusters_list[clusterid])):
			if int(article_id) == clusters_list[clusterid][j]:
				continue
			else:
				desired_cluster.append(clusters_list[clusterid][j])

		random.shuffle(desired_cluster)
		if(len(desired_cluster) <= 4):
			for art_no in desired_cluster:
				cursor.execute("SELECT * FROM articles WHERE article_id = %s", (art_no))
				news=cursor.fetchone()
				article1_infodict={'ArticleNo':news[0],'Headline':news[1],'Date':news[3],'Content':news[2],'Image':news[4],'GenreId':news[5],'Excited':news[8],'Happy':news[9],'Neutral':news[10],'Sad':news[11],'Morose':news[12]}
				ret_articles.append(article1_infodict)
		else:
			for art_no in desired_cluster[-4:]:
				cursor.execute("SELECT * FROM articles WHERE article_id = %s", (art_no))
				news=cursor.fetchone()
				article1_infodict={'ArticleNo':news[0],'Headline':news[1],'Date':news[3],'Content':news[2],'Image':news[4],'GenreId':news[5],'Excited':news[8],'Happy':news[9],'Neutral':news[10],'Sad':news[11],'Morose':news[12]}
				ret_articles.append(article1_infodict)		

	return render_template('articledisplay.html',username=str(uname),newsinfo=article_infodict,results=ret_articles)

@app.route('/1/<id>',methods=['GET','POST'])
def excited(id): 
	gen_id=id
	g_id=int(gen_id)
	rec_articles_dict=[]
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		
		if request.method == 'GET':			
			ul=1.0
			ll=0.5
			cursor.execute("SELECT * FROM articles WHERE genre_id=%s AND sentiment_score >0.5 LIMIT 4", (gen_id))
			articles=cursor.fetchall()
			for article in articles:
				article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
				rec_articles_dict.append(article_dict)
			
		random.shuffle(rec_articles_dict)
	return json.dumps(rec_articles_dict[:4])

@app.route('/2/<id>',methods=['GET','POST'])
def happy(id): 
	gen_id=id
	g_id=int(gen_id)
	rec_articles_dict=[]
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		
		if request.method == 'GET':			
			ul=0.5
			ll=0.0
			cursor.callproc('sp_getArticlesReactPos',(g_id,ul,ll))
			articles=cursor.fetchall()
			for article in articles:
				article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
				rec_articles_dict.append(article_dict)
			
		random.shuffle(rec_articles_dict)
	return json.dumps(rec_articles_dict[:4])

@app.route('/3/<id>',methods=['GET','POST'])
def neutral(id): 
	gen_id=id
	g_id=int(gen_id)
	rec_articles_dict=[]
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		
		if request.method == 'GET':
			ul=0.0
			cursor.callproc('sp_recneuart',(g_id,))
			articles=cursor.fetchall()
			for article in articles:
				article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
				rec_articles_dict.append(article_dict)
		
		random.shuffle(rec_articles_dict)
	return json.dumps(rec_articles_dict[:4])

@app.route('/4/<id>',methods=['GET','POST'])
def sad(id): 
	gen_id=id
	g_id=int(gen_id)
	rec_articles_dict=[]
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		
		if request.method == 'GET':			
			ul=0.0
			ll=-0.5			
			cursor.callproc('sp_getArticlesReactNeg',(g_id,ul,ll))
			articles=cursor.fetchall()
			for article in articles:
				article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
				rec_articles_dict.append(article_dict)
			
		random.shuffle(rec_articles_dict)
	return json.dumps(rec_articles_dict[:4])

@app.route('/5/<id>',methods=['GET','POST'])
def morose(id): 
	gen_id=id
	g_id=int(gen_id)
	rec_articles_dict=[]
	if 'user' in session:
		user_id=session['user']
		conn=mysql.connect()
		cursor=conn.cursor()
		cursor.execute("SELECT username FROM user WHERE user_no = %s", (user_id))
		uname=cursor.fetchone()[0]
		
		if request.method == 'GET':			
			ul=-0.5
			ll=-1.0			
			cursor.execute("SELECT * FROM articles WHERE genre_id=%s AND sentiment_score <-0.5 AND sentiment_score >=-1.0 LIMIT 4", (gen_id))

			articles=cursor.fetchall()
			for article in articles:
				article_dict={'ArticleId': article[0],'Headline':article[1], 'Date':article[3],'Summary':article[7],'Image':article[4] ,'GenreId': article[5],'Content':article[2],'Excited':article[8],'Happy':article[9],'Neutral':article[10],'Sad':article[11],'Morose':article[12]}
				rec_articles_dict.append(article_dict)
		
		random.shuffle(rec_articles_dict)
		
	return json.dumps(rec_articles_dict[:4])

@app.route('/logout')
def logout(): 
	session.pop('user',None)   
	return redirect('/')

if __name__ == '__main__':
	app.secret_key = 'jai mata di lets rocxxxx!!! RT' 
	app.debug = True
	app.run()

