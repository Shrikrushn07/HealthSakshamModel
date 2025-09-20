import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from openai import OpenAI

# Using a stable OpenAI model that works with the current SDK version
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

# Cache control for Replit environment
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

class HealthChatbot:
    def __init__(self):
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database with vaccination schedules and health data"""
        conn = sqlite3.connect('health_data.db')
        cursor = conn.cursor()
        
        # Create vaccination schedule table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vaccination_schedule (
                id INTEGER PRIMARY KEY,
                vaccine_name TEXT NOT NULL UNIQUE,
                age_group TEXT NOT NULL,
                description_en TEXT NOT NULL,
                description_hi TEXT NOT NULL,
                schedule TEXT NOT NULL
            )
        ''')
        
        # Create outbreak alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outbreak_alerts (
                id INTEGER PRIMARY KEY,
                disease TEXT NOT NULL,
                location TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                description_en TEXT NOT NULL,
                description_hi TEXT NOT NULL,
                date_created TEXT NOT NULL,
                UNIQUE(disease, location)
            )
        ''')
        
        # Insert vaccination data
        vaccinations = [
            ("BCG", "Birth", "Protection against tuberculosis", "तपेदिक से सुरक्षा", "At birth"),
            ("Hepatitis B", "Birth, 6 weeks, 10 weeks, 14 weeks", "Protection against Hepatitis B", "हेपेटाइटिस बी से सुरक्षा", "Birth, 6, 10, 14 weeks"),
            ("DPT", "6 weeks, 10 weeks, 14 weeks", "Protection against Diphtheria, Pertussis, Tetanus", "डिप्थीरिया, काली खांसी, टिटनेस से सुरक्षा", "6, 10, 14 weeks"),
            ("Polio", "Birth, 6 weeks, 10 weeks, 14 weeks", "Protection against Polio", "पोलियो से सुरक्षा", "Birth, 6, 10, 14 weeks"),
            ("Measles", "9-12 months", "Protection against Measles", "खसरा से सुरक्षा", "9-12 months"),
            ("MMR", "15-18 months", "Protection against Measles, Mumps, Rubella", "खसरा, कण्ठमाला, रूबेला से सुरक्षा", "15-18 months")
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO vaccination_schedule 
            (vaccine_name, age_group, description_en, description_hi, schedule)
            VALUES (?, ?, ?, ?, ?)
        ''', vaccinations)
        
        # Insert mock outbreak alerts
        alerts = [
            ("Dengue", "Delhi", "Medium", "Increased dengue cases reported. Use mosquito nets and avoid water stagnation.", "डेंगू के मामले बढ़े हैं। मच्छरदानी का उपयोग करें और पानी जमने न दें।", datetime.now().isoformat()),
            ("Malaria", "Mumbai", "High", "High malaria cases in monsoon season. Take preventive measures.", "मानसून में मलेरिया के अधिक मामले। बचाव के उपाय करें।", datetime.now().isoformat())
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO outbreak_alerts 
            (disease, location, alert_level, description_en, description_hi, date_created)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', alerts)
        
        conn.commit()
        conn.close()
    
    def detect_language(self, text):
        """Detect language of input text with support for Indian languages"""
        try:
            lang = detect(text)
            # Map various Indian languages to appropriate response language
            indian_languages = ['hi', 'bn', 'te', 'mr', 'ta', 'gu', 'kn', 'ml', 'pa', 'or', 'as', 'ur']
            
            if lang in indian_languages:
                return 'hi'  # Use Hindi for all Indian languages as fallback
            else:
                return 'en'  # English for others
        except (LangDetectException, Exception):
            # Check for common Hindi/Indian words as backup
            hindi_keywords = ['में', 'का', 'की', 'को', 'से', 'है', 'हैं', 'करें', 'लिए', 'साथ', 'बताइए', 'क्या', 'कैसे', 'यह', 'वह']
            text_lower = text.lower()
            
            if any(keyword in text_lower for keyword in hindi_keywords):
                return 'hi'
            else:
                return 'en'
    
    def get_health_system_prompt(self, language='en'):
        """Get specialized system prompt for health education"""
        if language == 'hi':
            return """आप एक विशेषज्ञ स्वास्थ्य शिक्षा चैटबॉट हैं जो ग्रामीण और अर्ध-शहरी आबादी की सेवा करते हैं। आपका लक्ष्य है:

1. सरल, स्पष्ट भाषा का उपयोग करना (कोई चिकित्सा शब्दजाल नहीं)
2. बीमारी के लक्षण, रोकथाम और टीकाकरण के बारे में सटीक जानकारी देना
3. तत्काल चिकित्सा सहायता की आवश्यकता होने पर "निकटतम स्वास्थ्य केंद्र जाएं" जैसी कार्रवाई योग्य सलाह देना
4. दोस्ताना और सहायक टोन बनाए रखना

हमेशा व्यावहारिक, समझने योग्य सलाह दें। यदि गंभीर लक्षण हों तो तुरंत डॉक्टर के पास जाने को कहें।"""
        else:
            return """You are an expert health education chatbot serving rural and semi-urban populations. Your goals are:

1. Use simple, clear language (no medical jargon)
2. Provide accurate information about disease symptoms, prevention, and vaccination
3. Give actionable advice like "Visit the nearest health center if..." when immediate medical attention is needed
4. Maintain a friendly and supportive tone

Always provide practical, understandable advice. For serious symptoms, always recommend immediate medical consultation."""
    
    def get_vaccination_info(self, language='en'):
        """Get vaccination schedule from database"""
        conn = sqlite3.connect('health_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM vaccination_schedule')
        vaccines = cursor.fetchall()
        conn.close()
        
        if language == 'hi':
            info = "टीकाकरण कार्यक्रम:\n\n"
            for vaccine in vaccines:
                info += f"• {vaccine[1]}: {vaccine[4]} - {vaccine[5]}\n"
        else:
            info = "Vaccination Schedule:\n\n"
            for vaccine in vaccines:
                info += f"• {vaccine[1]}: {vaccine[2]} - {vaccine[5]}\n"
        
        return info
    
    def get_outbreak_alerts(self, language='en'):
        """Get current outbreak alerts"""
        conn = sqlite3.connect('health_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM outbreak_alerts ORDER BY date_created DESC LIMIT 5')
        alerts = cursor.fetchall()
        conn.close()
        
        if not alerts:
            return "कोई वर्तमान प्रकोप अलर्ट नहीं है।" if language == 'hi' else "No current outbreak alerts."
        
        if language == 'hi':
            info = "वर्तमान स्वास्थ्य अलर्ट:\n\n"
            for alert in alerts:
                info += f"⚠️ {alert[2]} में {alert[1]} - {alert[3]} स्तर\n{alert[5]}\n\n"
        else:
            info = "Current Health Alerts:\n\n"
            for alert in alerts:
                info += f"⚠️ {alert[1]} in {alert[2]} - {alert[3]} level\n{alert[4]}\n\n"
        
        return info
    
    def get_realtime_health_data(self):
        """Get real-time health data from WHO and other APIs"""
        try:
            import requests
            # WHO Disease Outbreak News API
            who_response = requests.get('https://www.who.int/api/news/diseaseoutbreaknews', timeout=5)
            if who_response.status_code == 200:
                return who_response.json()
        except:
            pass
        return None

    def get_fallback_response(self, user_message, language='en'):
        """Provide comprehensive fallback responses when OpenAI is unavailable"""
        message_lower = user_message.lower()
        
        # Vaccination info
        if any(keyword in message_lower for keyword in ['vaccination', 'vaccine', 'टीका', 'टीकाकरण', 'immunization', 'प्रतिरक्षण']):
            return self.get_vaccination_info(language)
        
        # Outbreak alerts and real-time data
        elif any(keyword in message_lower for keyword in ['outbreak', 'alert', 'epidemic', 'प्रकोप', 'अलर्ट', 'pandemic', 'महामारी', 'current', 'latest', 'news', 'समाचार']):
            base_alerts = self.get_outbreak_alerts(language)
            realtime_data = self.get_realtime_health_data()
            if realtime_data:
                if language == 'hi':
                    return base_alerts + "\n\n🌐 नवीनतम स्वास्थ्य अपडेट WHO से प्राप्त किए गए हैं।"
                else:
                    return base_alerts + "\n\n🌐 Latest health updates retrieved from WHO."
            return base_alerts
        
        # COVID-19 related
        elif any(keyword in message_lower for keyword in ['covid', 'coronavirus', 'corona', 'कोरोना', 'कोविड']):
            if language == 'hi':
                return """COVID-19 के लक्षण और बचाव:
                
🦠 मुख्य लक्षण:
• बुखार
• सूखी खांसी
• सांस लेने में कठिनाई
• गले में खराश
• स्वाद और गंध का चले जाना
• थकान

🛡️ बचाव के उपाय:
• मास्क पहनें
• 6 फीट की दूरी बनाए रखें
• बार-बार हाथ धोएं (20 सेकंड)
• भीड़ से बचें
• वैक्सीन लगवाएं

⚠️ गंभीर लक्षण होने पर तुरंत डॉक्टर से संपर्क करें।"""
            else:
                return """COVID-19 Symptoms and Prevention:
                
🦠 Main Symptoms:
• Fever
• Dry cough
• Difficulty breathing
• Sore throat
• Loss of taste and smell
• Fatigue

🛡️ Prevention:
• Wear masks
• Maintain 6 feet distance
• Wash hands frequently (20 seconds)
• Avoid crowds
• Get vaccinated

⚠️ Seek immediate medical attention for severe symptoms."""
        
        # Fever and common symptoms
        elif any(keyword in message_lower for keyword in ['fever', 'बुखार', 'temperature', 'तापमान', 'hot', 'गर्म']):
            if language == 'hi':
                return """बुखार का उपचार और देखभाल:
                
🌡️ बुखार के कारण:
• संक्रमण (वायरल/बैक्टीरियल)
• डेंगू/मलेरिया
• टाइफाइड
• COVID-19

💊 घरेलू उपचार:
• पर्याप्त आराम करें
• अधिक तरल पदार्थ पिएं
• हल्का भोजन लें
• गुनगुने पानी से पोंछें
• पैरासिटामोल ले सकते हैं

⚠️ तुरंत डॉक्टर से मिलें यदि:
• 102°F से ज्यादा बुखार
• 3 दिन से ज्यादा बुखार
• सांस लेने में दिक्कत
• चक्कर आना या बेहोशी"""
            else:
                return """Fever Treatment and Care:
                
🌡️ Fever Causes:
• Infections (viral/bacterial)
• Dengue/Malaria
• Typhoid
• COVID-19

💊 Home Treatment:
• Take adequate rest
• Drink plenty of fluids
• Eat light food
• Sponge with lukewarm water
• Take paracetamol if needed

⚠️ See doctor immediately if:
• Fever above 102°F
• Fever for more than 3 days
• Difficulty breathing
• Dizziness or fainting"""
        
        # Diabetes
        elif any(keyword in message_lower for keyword in ['diabetes', 'डायबिटीज', 'मधुमेह', 'sugar', 'blood sugar', 'insulin', 'इंसुलिन']):
            if language == 'hi':
                return """मधुमेह (डायबिटीज) की जानकारी:
                
🩺 लक्षण:
• बार-बार पेशाब आना
• अधिक प्यास लगना
• भूख बढ़ना
• वजन कम होना
• थकान
• घाव धीरे भरना

🍎 आहार सुझाव:
• चीनी और मिठाई से बचें
• साबुत अनाज खाएं
• हरी सब्जियां शामिल करें
• नियमित भोजन का समय रखें

💊 नियंत्रण:
• नियमित दवा लें
• रोज व्यायाम करें
• ब्लड शुगर चेक करें
• डॉक्टर से मिलते रहें

⚠️ तत्काल सहायता यदि ब्लड शुगर बहुत कम या ज्यादा हो।"""
            else:
                return """Diabetes Information:
                
🩺 Symptoms:
• Frequent urination
• Excessive thirst
• Increased hunger
• Weight loss
• Fatigue
• Slow wound healing

🍎 Diet Suggestions:
• Avoid sugar and sweets
• Eat whole grains
• Include green vegetables
• Maintain regular meal times

💊 Management:
• Take medicines regularly
• Exercise daily
• Monitor blood sugar
• Regular doctor visits

⚠️ Seek immediate help if blood sugar is very low or high."""
        
        # Pregnancy and maternal health
        elif any(keyword in message_lower for keyword in ['pregnancy', 'pregnant', 'गर्भावस्था', 'गर्भवती', 'prenatal', 'maternal', 'baby', 'बच्चा']):
            if language == 'hi':
                return """गर्भावस्था की देखभाल:
                
🤱 महत्वपूर्ण सुझाव:
• नियमित चेकअप कराएं
• फोलिक एसिड लें
• आयरन की गोलियां लें
• संतुलित आहार लें
• धूम्रपान-शराब से बचें

🍎 आहार:
• दूध और दूध के उत्पाद
• हरी पत्तेदार सब्जियां
• फल
• प्रोटीन युक्त भोजन
• पर्याप्त पानी

⚠️ तुरंत डॉक्टर से मिलें यदि:
• खून आना
• तेज पेट दर्द
• तेज सिरदर्द
• बुखार
• उल्टी रुकना नहीं"""
            else:
                return """Pregnancy Care:
                
🤱 Important Tips:
• Regular prenatal checkups
• Take folic acid
• Take iron supplements
• Eat balanced diet
• Avoid smoking and alcohol

🍎 Diet:
• Milk and dairy products
• Green leafy vegetables
• Fruits
• Protein-rich foods
• Adequate water

⚠️ See doctor immediately if:
• Bleeding
• Severe abdominal pain
• Severe headache
• Fever
• Persistent vomiting"""
        
        # Hypertension/Blood Pressure
        elif any(keyword in message_lower for keyword in ['pressure', 'hypertension', 'bp', 'blood pressure', 'हाई ब्लड प्रेशर', 'उच्च रक्तचाप']):
            if language == 'hi':
                return """उच्च रक्तचाप (हाई ब्लड प्रेशर):
                
🩺 लक्षण:
• सिरदर्द
• चक्कर आना
• सीने में दर्द
• सांस फूलना
• नकसीर आना

🥗 जीवनशैली बदलाव:
• नमक कम करें
• वजन नियंत्रित करें
• नियमित व्यायाम
• धूम्रपान छोड़ें
• तनाव कम करें
• पर्याप्त नींद लें

📊 सामान्य रेंज: 120/80 mmHg
📊 उच्च: 140/90 mmHg से ज्यादा

⚠️ अगर 180/120 से ज्यादा हो तो तुरंत अस्पताल जाएं।"""
            else:
                return """High Blood Pressure (Hypertension):
                
🩺 Symptoms:
• Headache
• Dizziness
• Chest pain
• Shortness of breath
• Nosebleeds

🥗 Lifestyle Changes:
• Reduce salt intake
• Maintain healthy weight
• Regular exercise
• Quit smoking
• Reduce stress
• Get adequate sleep

📊 Normal Range: 120/80 mmHg
📊 High: Above 140/90 mmHg

⚠️ If above 180/120, go to hospital immediately."""
        
        # Mental health
        elif any(keyword in message_lower for keyword in ['depression', 'anxiety', 'stress', 'mental health', 'अवसाद', 'चिंता', 'तनाव', 'मानसिक स्वास्थ्य']):
            if language == 'hi':
                return """मानसिक स्वास्थ्य की देखभाल:
                
🧠 सामान्य समस्याएं:
• अवसाद (डिप्रेशन)
• चिंता (एंग्जायटी)
• तनाव
• नींद की समस्या

💪 सुधार के उपाय:
• नियमित व्यायाम करें
• योग और ध्यान
• परिवार-दोस्तों से बात करें
• शौक में समय बिताएं
• पर्याप्त नींद लें
• स्वस्थ आहार लें

📞 मदद कहाँ से मिले:
• पारिवारिक डॉक्टर
• मनोवैज्ञानिक/साइकोलॉजिस्ट
• हेल्पलाइन: 91-9152987821

⚠️ आत्महत्या के विचार आने पर तुरंत मदद लें।"""
            else:
                return """Mental Health Care:
                
🧠 Common Issues:
• Depression
• Anxiety
• Stress
• Sleep problems

💪 Improvement Tips:
• Regular exercise
• Yoga and meditation
• Talk to family/friends
• Spend time on hobbies
• Get adequate sleep
• Eat healthy diet

📞 Where to Get Help:
• Family doctor
• Psychologist/Psychiatrist
• Helpline: 91-9152987821

⚠️ If having suicidal thoughts, seek immediate help."""
        
        # First Aid
        elif any(keyword in message_lower for keyword in ['first aid', 'emergency', 'accident', 'injury', 'प्राथमिक चिकित्सा', 'आपातकाल', 'दुर्घटना', 'चोट']):
            if language == 'hi':
                return """प्राथमिक चिकित्सा (First Aid):
                
🩹 मामूली चोट:
• घाव को साफ पानी से धोएं
• एंटीसेप्टिक लगाएं
• पट्टी बांधें
• टेटनेस इंजेक्शन लगवाएं

🔥 जलना:
• तुरंत ठंडे पानी में डालें
• बर्फ न लगाएं
• मक्खन या तेल न लगाएं
• डॉक्टर को दिखाएं

🤕 बेहोशी:
• सिर नीचे पैर ऊपर करें
• हवादार जगह ले जाएं
• चेहरे पर पानी छिड़कें
• 108 डायल करें

☎️ आपातकाल नंबर: 108, 102"""
            else:
                return """First Aid Emergency Care:
                
🩹 Minor Injuries:
• Clean wound with water
• Apply antiseptic
• Bandage the wound
• Get tetanus injection

🔥 Burns:
• Immediately put in cold water
• Don't use ice
• Don't apply butter or oil
• See a doctor

🤕 Fainting:
• Keep head down, legs up
• Move to ventilated area
• Sprinkle water on face
• Call 108

☎️ Emergency Numbers: 108, 102"""
        
        # Child health
        elif any(keyword in message_lower for keyword in ['child', 'baby', 'infant', 'बच्चा', 'शिशु', 'pediatric', 'children']):
            if language == 'hi':
                return """बच्चों का स्वास्थ्य:
                
👶 0-6 महीने:
• केवल मां का दूध
• नियमित टीकाकरण
• वजन की निगरानी

👧 6 महीने-2 साल:
• मां का दूध + ऊपरी आहार
• दाल, चावल, सब्जी का पानी
• फलों का रस

🧒 2-5 साल:
• संतुलित आहार
• हाथ धोने की आदत
• खेल-कूद

⚠️ तुरंत डॉक्टर को दिखाएं यदि:
• तेज बुखार
• दस्त-उल्टी
• सांस लेने में दिक्कत
• खाना-पीना बंद करना"""
            else:
                return """Child Health Care:
                
👶 0-6 months:
• Exclusive breastfeeding
• Regular vaccinations
• Weight monitoring

👧 6 months-2 years:
• Breast milk + complementary food
• Dal, rice, vegetable water
• Fruit juices

🧒 2-5 years:
• Balanced diet
• Hand washing habits
• Physical play

⚠️ See doctor immediately if:
• High fever
• Diarrhea/vomiting
• Difficulty breathing
• Refusing food/water"""
        
        # Common symptoms
        elif any(keyword in message_lower for keyword in ['headache', 'cough', 'cold', 'stomach pain', 'सिरदर्द', 'खांसी', 'सर्दी', 'पेट दर्द']):
            if language == 'hi':
                return """सामान्य लक्षणों का इलाज:
                
🤕 सिरदर्द:
• आराम करें, आंखें बंद करें
• माथे पर ठंडा पानी रखें
• पैरासिटामोल ले सकते हैं
• मालिश करें

🤧 सर्दी-खांसी:
• गर्म पानी पिएं
• शहद-अदरक का काढ़ा
• भाप लें
• आराम करें

🤢 पेट दर्द:
• हल्का भोजन करें
• अधिक पानी पिएं
• गर्म सेक दें
• तली-मसालेदार चीजों से बचें

⚠️ अगर लक्षण 2-3 दिन में न जाएं तो डॉक्टर को दिखाएं।"""
            else:
                return """Common Symptoms Treatment:
                
🤕 Headache:
• Rest with eyes closed
• Apply cold water on forehead
• Take paracetamol if needed
• Gentle massage

🤧 Cold-Cough:
• Drink warm water
• Honey-ginger decoction
• Take steam
• Get rest

🤢 Stomach Pain:
• Eat light food
• Drink more water
• Apply warm compress
• Avoid fried/spicy food

⚠️ If symptoms persist for 2-3 days, see a doctor."""
        
        # Nutrition and diet
        elif any(keyword in message_lower for keyword in ['nutrition', 'diet', 'food', 'healthy eating', 'पोषण', 'आहार', 'भोजन', 'खाना']):
            if language == 'hi':
                return """स्वस्थ आहार और पोषण:
                
🥗 संतुलित आहार में शामिल करें:
• अनाज (चावल, गेहूं, बाजरा)
• दालें (प्रोटीन के लिए)
• सब्जियां (विटामिन-मिनरल)
• फल (विटामिन सी)
• दूध-दही (कैल्शियम)

💧 पानी:
• दिन में 8-10 गिलास पानी पिएं
• भोजन से पहले-बाद में पानी न पिएं

🚫 बचने योग्य:
• अधिक तेल-मसाला
• जंक फूड
• मिठाई
• कोल्ड ड्रिंक

⏰ भोजन का समय नियमित रखें।"""
            else:
                return """Healthy Diet and Nutrition:
                
🥗 Include in balanced diet:
• Grains (rice, wheat, millets)
• Pulses (for protein)
• Vegetables (vitamins-minerals)
• Fruits (vitamin C)
• Milk-yogurt (calcium)

💧 Water:
• Drink 8-10 glasses per day
• Don't drink water before/after meals

🚫 Avoid:
• Excessive oil and spices
• Junk food
• Sweets
• Cold drinks

⏰ Maintain regular meal times."""
        
        # Elderly care
        elif any(keyword in message_lower for keyword in ['elderly', 'old age', 'senior', 'बुजुर्ग', 'बूढ़े', 'वृद्ध']):
            if language == 'hi':
                return """बुजुर्गों की देखभाल:
                
👴 सामान्य समस्याएं:
• जोड़ों का दर्द
• ब्लड प्रेशर
• डायबिटीज
• आंखों की कमजोरी
• भूलने की बीमारी

💊 देखभाल:
• नियमित दवा दें
• हल्का व्यायाम कराएं
• संतुलित आहार दें
• समय पर सुलाएं
• साफ-सफाई रखें

🏥 नियमित जांच:
• ब्लड प्रेशर चेक करें
• ब्लड शुगर टेस्ट
• आंखों की जांच
• दांतों की देखभाल

❤️ मानसिक सहारा और प्यार देना जरूरी है।"""
            else:
                return """Elderly Care:
                
👴 Common Problems:
• Joint pain
• Blood pressure
• Diabetes
• Vision problems
• Memory issues

💊 Care Tips:
• Give medicines regularly
• Light exercise
• Balanced diet
• Regular sleep schedule
• Maintain hygiene

🏥 Regular Checkups:
• Blood pressure monitoring
• Blood sugar tests
• Eye examinations
• Dental care

❤️ Emotional support and love are essential."""
        
        # Default response - now more comprehensive
        else:
            if language == 'hi':
                return """🏥 मैं आपका स्वास्थ्य सहायक हूं। मैं निम्नलिखित विषयों में मदद कर सकता हूं:

🩺 बीमारियां और लक्षण:
• COVID-19, डेंगू, मलेरिया
• डायबिटीज, हाई ब्लड प्रेशर
• बुखार, सिरदर्द, खांसी

👶 विशेष देखभाल:
• गर्भावस्था की देखभाल
• बच्चों का स्वास्थ्य
• बुजुर्गों की देखभाल

💊 स्वास्थ्य सेवाएं:
• टीकाकरण कार्यक्रम
• प्राथमिक चिकित्सा
• पोषण और आहार
• मानसिक स्वास्थ्य

📍 वर्तमान अलर्ट और समाचार भी उपलब्ध हैं।

कृपया अपना स्वास्थ्य संबंधी प्रश्न पूछें!"""
            else:
                return """🏥 I'm your comprehensive health assistant. I can help with:

🩺 Diseases & Symptoms:
• COVID-19, Dengue, Malaria
• Diabetes, High Blood Pressure
• Fever, Headache, Cough

👶 Special Care:
• Pregnancy care
• Child health
• Elderly care

💊 Health Services:
• Vaccination schedules
• First aid
• Nutrition and diet
• Mental health

📍 Current alerts and real-time health news available.

Please ask your health-related question!"""

    def generate_response(self, user_message, language='en'):
        """Generate AI response using OpenAI with fallback"""
        try:
            # Check if user is asking for vaccination info
            if any(keyword in user_message.lower() for keyword in ['vaccination', 'vaccine', 'टीका', 'टीकाकरण']):
                vaccination_info = self.get_vaccination_info(language)
                prompt = f"User is asking about vaccinations. Here's the vaccination schedule data:\n{vaccination_info}\n\nUser question: {user_message}\n\nPlease provide a helpful response using this information."
            
            # Check if user is asking for outbreak alerts
            elif any(keyword in user_message.lower() for keyword in ['outbreak', 'alert', 'epidemic', 'प्रकोप', 'अलर्ट']):
                outbreak_info = self.get_outbreak_alerts(language)
                prompt = f"User is asking about health alerts/outbreaks. Here's the current alert data:\n{outbreak_info}\n\nUser question: {user_message}\n\nPlease provide a helpful response using this information."
            
            else:
                prompt = user_message
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.get_health_system_prompt(language)},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI API Error: {str(e)}")  # Add error logging
            # Return fallback response instead of generic error
            return self.get_fallback_response(user_message, language)

# Initialize chatbot
chatbot = HealthChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        user_message = data.get('message', '').strip()
        preferred_language = data.get('preferred_language', 'en')  # Get user's language preference
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Use preferred language if provided, otherwise detect
        if preferred_language in ['hi', 'en']:
            detected_language = preferred_language
        else:
            detected_language = chatbot.detect_language(user_message)
        
        # Generate response - always return 200 with fallback if needed
        try:
            response = chatbot.generate_response(user_message, detected_language)
        except Exception as e:
            print(f"OpenAI API failed, using fallback: {str(e)}")
            response = chatbot.get_fallback_response(user_message, detected_language)
        
        return jsonify({
            'response': response,
            'detected_language': detected_language,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Chat endpoint error: {str(e)}")
        # Always return fallback response with 200 status
        try:
            safe_message = user_message if 'user_message' in locals() and user_message else "हैलो"
            fallback_response = chatbot.get_fallback_response(safe_message, 'hi')
            return jsonify({
                'response': fallback_response,
                'detected_language': 'hi',
                'timestamp': datetime.now().isoformat()
            }), 200
        except:
            return jsonify({
                'response': 'मैं स्वास्थ्य मित्र हूं। कैसे मदद कर सकता हूं?',
                'detected_language': 'hi',
                'timestamp': datetime.now().isoformat()
            }), 200

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Add missing /api endpoint to stop 404 errors  
@app.route('/api', methods=['GET', 'HEAD'])
def api_health():
    return jsonify({
        'status': 'ok',
        'service': 'Health Mitra API',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)