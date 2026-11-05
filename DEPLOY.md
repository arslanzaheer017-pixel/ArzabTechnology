# ARZAB website + AI agent ko 24/7 online karna (PythonAnywhere, free)

Is ke baad na terminal chalana parega, na computer on rakhna parega.
Link milega: https://TUMHARA_USERNAME.pythonanywhere.com

## Pehle ye files ek folder mein jama karo
```
Arzab/
  app.py
  requirements.txt
  templates/home.html      (website)
  templates/index.html     (full chat page)
  static/script.js
  static/style.css
```
`.env` aur `database.db` upload NAHI karni (database online khud ban jayega).

## Step 1: Account
1. pythonanywhere.com par free "Beginner" account banao (username soch kar rakho, wohi link ban jayega).

## Step 2: Files upload
1. Dashboard > **Files** > `mysite` ya naya folder `Arzab` banao.
2. Upar wali saari files (folders samet) wahan upload karo.
3. Same folder mein **.env** naam ki file banao (Files page par "New file"), aur ye likho:
   ```
   GROQ_API_KEY=gsk_apni_key_yahan
   ```
   Key kisi ko mat dikhana, aur GitHub par mat daalna.

## Step 3: Libraries install
1. Dashboard > **Consoles** > **Bash**.
2. Chalao:
   ```
   cd ~/Arzab
   pip install --user -r requirements.txt
   ```

## Step 4: Web app banao
1. Dashboard > **Web** > **Add a new web app** > **Manual configuration** > Python 3.10 ya naya.
2. **Source code** aur **Working directory**: `/home/TUMHARA_USERNAME/Arzab`
3. **WSGI configuration file** ka link kholo, sara purana code hata kar sirf ye likho:
   ```python
   import sys
   path = "/home/TUMHARA_USERNAME/Arzab"
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application
   ```
4. **Static files** mein: URL `/static/` , Directory `/home/TUMHARA_USERNAME/Arzab/static`
5. Upar green **Reload** button dabao.

Phir `https://TUMHARA_USERNAME.pythonanywhere.com` kholo. Website aur "Chat with agent" chalna chahiye.

## Zaroori: har mahine ek click
Free plan par web app **1 mahine baad expire** ho jati hai. Web page par
**"Run until 1 month from today"** button dabana hota hai (mahine mein ek baar).
Phone mein reminder laga lo.

## Agar masla ho
- Web page > **Error log**: asli error yahin likha hota hai.
- Code badla ho to **Reload** dabao.
- `/health` kholo (`.../health`): `{"status":"ok"}` aaye to server theek hai.

## Baad mein (jab serious ho jao)
Free plan par custom domain (arzab.com), zyada CPU aur automatic reminders nahi milte.
Jab ARZAB ka asli launch ho to paid plan lena behtar hai.
