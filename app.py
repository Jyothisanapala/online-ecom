from flask import Flask,request,render_template,url_for,redirect,flash,abort,session
import mysql.connector
from flask_session import Session
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from key import secret_key,salt,salt2,salt3
from cmail import sendmail
#from otp import adotp
import os
from io import BytesIO
import re
import stripe
stripe.api_key='sk_test_51OJUojSAF4gqgxsPDx1JVr61FGwbsFzExEqPEC58vrReoWQL4oaciedx8PDH8FHUThAXS2ZucZIeXDHTeZpWg5BY00e6ZLXtxY'
mydb=mysql.connector.connect(host='localhost',user='root',password='Admin',db='ecom')
app=Flask(__name__)

app.secret_key=secret_key
session(app)
app.config['SESSION_TYPE']='filesystem'
@app.route('/')
def index():
    return render_template('welcome.html')
@app.route('/homepage')
def home():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to-uuid(),item_name,dis,qty,category,price,addedby from additems')
    items=cursor.fetchall()
    return render_template('home1.html',items=items)
@app.route('/signup',methods=['GET','POST'])
def usignup():
    if request.method=='POST':
        user=request.form['name']
        mobile=request.form['mobile']
        email=request.form['email']
        address=request.form['address']
        gender=request.form['gender']
        password=request.form['password']
        #print(user,mobile,email,address,gender,password)
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from users where email=%s',[email])
            count=cursor.fetchone()[0]
            print(count)
            if count==1:
                raise Exception
        except Exception as e:
            flash('User alredy registered')
            return redirect(url_for('home'))
        else:
            data={'user':user,'email':email,'mobile':mobile,'address':address,'gender':gender,'password':password}
            subject='The confirmation link has sent to Email'
            body=f"Click the link to confirm{url_for('confirm',token=token(data,salt=salt),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Link has sent to this Mail')
            return redirect(url_for('login'))
    return render_template('signup.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        user=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select user_name,password from users where user_name=%s and password=%s',[user,password])
        count=cursor.fetchone()
        if count==(user,password):
            session['user']=user
            if not session.get('user'):
                session['user']=user
            return redirect(url_for('home'))
    return render_template('login.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into users(user_id,user_name,u_mobile,email,gender,address,password) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s)',[data['user'],data['mobile'],data['email'],data['gender'],data['address'],data['password']])
        mydb.commit()
        cursor.close()
        flash('Details Registered successfully')
        return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    return redirect(url_for('login'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['id']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        try:
            if count!=1:
                raise Exception
        except Exception as e:
            flash('Pls Register for the application')
            return redirect(url_for('index'))
        else:
            subject='Reset link for ecom application'
            body=f"The reset link for ecom application: {url_for('uforgot',token=token(email,salt=salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Reset Link has sent to give email pls check.')
            return redirect(url_for('forgot'))
    return render_template('forgot.html')
@app.route('/uforgot/<token>',methods=['GET','POST'])
def uforgot(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Reset link expired')
    else:
        if request.method=='POST':
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',[npassword,data])
                mydb.commit()
                cursor.close()
                flash('Password has updated')
                return redirect(url_for('login'))
            else:
                flash('Mismatched  confirmation password')
                return render_template('newpassword.html')
        return render_template('newpassword.html')
@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        a_id=adotp()
        admin=request.form['name']
        aemail=request.form['email']
        amobile=request.form['mobile']
        password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            print('hi')
            cursor.execute('select count(*) from admindetails where admin_email=%s',[aemail])
            count=cursor.fetchone()[0]
            print(count)
            if count==1:
                raise Exception
        except Exception as e:
            flash('User alredy existed')
            return redirect(url_for('index'))
        else:
            serializer=URLSafeTimedSerializer(secret_key)
            data=serializer.dumps(a_id,salt=salt3)
            subject='OTP for ecom application'
            body=f"This is the otp for your account creation: {a_id}"
            sendmail(to=aemail,subject=subject,body=body)
            flash('The otp has sent to given mail')
            return redirect(url_for('adminverify',data=data,admin=admin,aemail=aemail,amobile=amobile,password=password))
        
    return render_template('adminsignup.html') 
@app.route('/adminverify/<data>/<admin>/<aemail>/<amobile>/<password>',methods=['GET','POST'])
def adminverify(data,admin,aemail,amobile,password):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        otp=serializer.loads(data,salt=salt3,max_age=180)
        
    except:
        abort(404,'OTP has expired')
    else:
        if request.method=='POST':
            print(otp)
            uotp=request.form['adminotp']
            print(uotp)
            if otp==uotp:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admindetails(admin_id,admin_name,admin_mobile,admin_email,password) values(%s,%s,%s,%s,%s)',[uotp,admin,amobile,aemail,password])
                mydb.commit()
                cursor.close()
                flash('Details Registered successfully')
                return redirect(url_for('adminlogin'))
    return render_template('adminotp.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if session.get('user'):
        return redirect(url_for('admindashboard'))
    if request.method=='POST':
        auser=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select admin_email,password from admindetails where admin_email=%s and password=%s',[auser,password])
        count=cursor.fetchone()
        if count==(auser,password):
            session['auser']=auser
            return redirect(url_for('admindash'))
    return render_template('adminlogin.html')
@app.route('/aforgot',methods=['GET','POST'])
def aforgot():
    if request.method=='POST':
        email=request.form['id']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admindetails where admin_email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        try:
            if count!=1:
                raise Exception
        except Exception as e:
            flash('Pls Register for the application')
            return redirect(url_for('index'))
        else:
            subject='Admin Reset link for ecom application'
            body=f"The reset link for ecom application: {url_for('averify',token=token(email,salt=salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Reset Link has sent to give email pls check.')
            return redirect(url_for('aforgot'))
    return render_template('adminforgot.html')
@app.route('/averify/<token>',methods=['GET','POST'])
def averify(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Reset link expired')
    else:
        if request.method=='POST':
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admindetails set password=%s where admin_email=%s',[npassword,data])
                mydb.commit()
                cursor.close()
                flash('Password has updated')
                return redirect(url_for('adminlogin'))
            else:
                flash('Mismatched  confirmation password')
                return render_template('adminnewpassword.html')
    return render_template('adminnewpassword.html')
@app.route('/admindashboard')
def admindash():
    return render_template('admindashboard.html')
@app.route('/alogout')
def alogout():
    if session.get('auser'):
        session.pop('auser')
        return redirect(url_for('adminlogin'))
    return redirect(url_for('login'))
@app.route('/additems',methods=['GET','POST'])
def additems():
    if session.get('user'):
        if request.method=='POST':
            item_name=request.form['name']
            desc=request.form['desc']
            qty=request.form['qty']
            category=request.form['category']
            price=request.form['price']
            addedby=session.get('user')
            image=request.files['image']
            filename=adotp()+'.jpg'
            path=os.path.dirname(os.path.absolute(__file__))
            static_path=os.path.join(path,'static')
            image.save(os.path.join(static_path,filenmae))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into additems(item_id,item_name,dis,qty,catergory,price,addedby,imgid) values(uuid_to_bi(uuid()),%s,%s,%s,%s,%s,%s)',[item_name,desc,qty,category,price,addedby,filename])
            mydb.commit()
            cursor.close()
            flash('Item added Successfully')
            return redirect(url_for('additem'))
@app.route('/pstatus')
def pstatus():
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,dis,qty,category,price from additems where addedby=%s',[session.get('user')])
        items=cursor.fetchall()
        cursor.close()
    return render_template('status.html',items=items)
@app.route('/update/<itemid>',methods=['SET','POST'])
def update(itemid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select item_name,dis,qyt,category,price from additems where item_id=uuid_to_bin(%s)',[itemid])
        data=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            item_name=request.form['name']
            desc=request.form['desc']
            qyt=request.form['qty']
            category=request.form['category']
            price=request.form['price']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update additems set item_name=%s,dis=%s,qyt=%s,category=%s,price=%s where item_id=uuid_to_bin(%s)',[item_name,desc,qyt,category,price,itemid])
            mydb.commit()
            cursor.close()
            flash('Item details Updated successfully')
            return redirect(url_for('pstatus'))
    return render_template('updateproducts.html',data=data)
@app.route('/pdelete/<itemid>')
def delete(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from additems where item_id=uuid_to_bin(%s) and addedby',[itemid,session.get('user')])
    mydb.commit()
    cursor.close()
    flah('Item details are succcessfully Deleted')
    filename=adotp()+'.jpg'
    path=os.path.dirname(os.path.absolute(__file__))
    static_path=os.path.join(path,'static')
    image.remove(os.path.join(static_path,filenmae))
    flah('Item details are succcessfully Deleted')
    return redirect(url_For('pstatus'))
@app.route('/contactus',methods=['GET','POST'])
def contactus():
    if request.method=='POST':
        name=request.form['name']
        emailid=request.form['emailid']
        msg=request.form['msg']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into contactus(name,emailid,message) values(%s,%s,%s)',[name,emailid,msg])
        mydb.commit()
        cursor.close()
        flash('report sent successfully')
        return redirect(url_for('contactus.html'))
    return render_template('contact.html')
@app.route('/readvontact')
def readcontact():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from contactus')
    contact=cursor.fetchall()
    return render_template('readcontact.html',contact=contact)
@app.route('/dashboard/<category>')
def dashboard(category):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select uuid_to_bin(item_id),item_name,dis,qty,price from additems where category=%s',[category])
    items=cursor.fetchall()
    return render_template('dashboard.html',items=items)
@app.route('/dashboardpage')
def allitems():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(item_id),item_name,dis,qty,category,price,imgid from additems')
    items=cursor.fetchall()
    return render_template('dashboard.html',items=items)
@app.route('/cart/<itemid>/<itemname>/<desc>/<category>/<price>/<imgid>')
def cart(itemid,itemname,desc,category,price,imgid):
    if not session.get('user'):
        return redirect(url_for('login'))
    if itemid not in session[session.get('user')]:
        session[session.get('user')][itemid]=[name,dis,1,price]
        session.modified=True
        flash(f'{name} added to cart')
        return redirect(url_for('dashboard',category=category))
    session[session.get('user')][itemid][2]==1
    flash('Item already existed')
    return redirect(url_for('dashboard',category=category))
@app.route('/viewcart')
def viewcart():
    if not session.get('user'):
        return redirect(url_for('login'))
    items=session[session.get('user')] if session.get(session.get('user')) else 'empty'
    if itemid=='empty':
        return 'No product in cart'
    return render_template('cart.html',items=items)
@app.route('/rem/<item>')
def rem(item):
    if session.get('user'):
        session[session.get('user')].pop(item)
        return redirect(url_for('viewcart'))
    return redirect(url_for('login'))
@app.route('/dis/<itemid>')
def dis(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(item_id),item_name,dis,category,price,imgid from additems where item_id=uuid_to_bin(%s)',[itemid])
    items=cursor.fetchone()
    cursor.close()
    return render_template('discription.html',items=items)
@app.route('/writereview/<itemid>',methods=['GET','POST'])
def wreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            user=session.get('user')
            title=request.form['title']
            desc=request.form['decs']
            rate==request.form['rate']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into reviews(itemid,user,title,review,rating) values(uuid_to_bin()%s,%s,%s,%s)',[itemid,user,title,desc,rate])
            mydb.commit()
            cursor.close()
            flash('Thank you for the feedback')
        return render_template('review.html')
    return redirect(url_for('login'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        name=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}',re.IGNOCASE)
        if pattern.match(name):
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,dis,qty,category,price from additems where where item_name like %s',[name + %s])
            data=cursor.fetchall()
            cursor.close()
        else:
            flash('No items found')
    return render_template('home1.html')
@app.route('/readreview/<itemid>')
def rreview(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select itemid,user,title,review,rating,dare from reviews where itemid=bin_to_uuid')
    reviews=cursor.fetchall()
    cursor.close()
    return render_template('readreview.html')
@app.route('/pay/<itemid>/<name>/<nt:price>',methods='POST')
def pay(itemid,price,name):
    if session.get('user'):
        q=int(request.form['qty'])
        username=session.get('user')
        total=price*qty
        chechout_session=stripe.checkout.session,create(
            success_url=url_for('success',itemid=itemid,name=name,q=q,total=total,_external=True)
            line_items=[
                {
                    'price_data':{
                        'product_data':{
                            'name':name,
                        },
                        'unit_amount':price*100,
                        'currency':'inr',
                    },
                    'quantity':q,
                },
                ],
            mode="payment",)
        return redirect(chechout_session.url)
    else:
        retuen redirect(url_for('login'))
@app.route('/success/<itemid>/<name>/<q>/<total>')
def success(itemid,name,q,total):
    user=session.get('user')
    cursor=mydb.cursor(buffered=True)
    cursor.execute('insert into orders(itemid,item_name,qty,total_price,user) values(%s,%s,%s,%s,%s)')
    mydb.commit()
    cursor.close()
    return 'order placed'
app.run()