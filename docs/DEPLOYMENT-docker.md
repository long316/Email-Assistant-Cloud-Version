# 閮ㄧ讲鎸囧崡锛圖ocker + Nginx + HTTPS锛?
鏈枃妗ｆ寚瀵间綘灏嗛偖浠跺姪鎵嬩互 Docker 閮ㄧ讲鍒版湇鍔″櫒锛屽苟閫氳繃 Nginx 鎻愪緵 HTTPS 涓庡弽鍚戜唬鐞嗐€?
鍓嶇疆鏉′欢锛?- 宸插畬鎴愬煙鍚嶈В鏋愯嚦鏈嶅姟鍣紙濡傦細mail.influzzde.top锛?- 宸查厤缃?Nginx 涓庤瘉涔︼紙443 鍙闂級
- 鍦?Google Cloud Console 鍒涘缓 OAuth Web 瀹㈡埛绔紝骞跺～鍐欓噸瀹氬悜 URI锛?  - `https://mail.influzzde.top/oauth/google/callback`

## 1. 鍑嗗椤圭洰涓庣洰褰?
鍦ㄦ湇鍔″櫒涓婂噯澶囦互涓嬬洰褰曠粨鏋勶紙绀轰緥锛歚/opt/email-assistant`锛夛細

```
/opt/email-assistant/
鈹溾攢 files/           # 闄勪欢涓庡浘鐗囷紙浼氭寕杞藉埌瀹瑰櫒 /app/files锛?鈹? 鈹斺攢 pics/
鈹溾攢 logs/            # 鏃ュ織锛堜細鎸傝浇鍒板鍣?/app/logs锛?鈹溾攢 secrets/         # 鏀剧疆 Google OAuth 瀹㈡埛绔嚟鎹紙鍙鎸傝浇缁欏鍣級
鈹? 鈹斺攢 credentials.json
鈹溾攢 token_store/     # token_*.json 瀛樻斁鐩綍锛堜笌鏈湴鍏煎锛?鈹溾攢 docker-compose.yml
鈹溾攢 Dockerfile
鈹溾攢 .env             # 鐜鍙橀噺锛堝弬鑰?.env.example锛?鈹斺攢 椤圭洰婧愪唬鐮?..
```

灏?`credentials.json` 鏀惧叆 `secrets/` 鐩綍銆?
## 2. 閰嶇疆鐜鍙橀噺锛?env锛?
鍦ㄤ粨搴撴牴鐩綍鍒涘缓 `.env`锛堝彲澶嶅埗 `.env.example` 骞惰皟鏁达級锛?
```
AUTH_FLOW=web
OAUTH_REDIRECT_URL=https://mail.influzzde.top/oauth/google/callback
API_KEY=YOUR_STRIPE_API_KEY
```

璇存槑锛?- `AUTH_FLOW`锛氫娇鐢?Web 鎺堟潈娴佺▼
- `OAUTH_REDIRECT_URL`锛氬繀椤讳笌 GCP 鎺у埗鍙颁腑鐨勯噸瀹氬悜 URI 瀹屽叏涓€鑷?- `API_KEY`锛氳皟鐢ㄥ彂閫佷笌鎺у埗绫绘帴鍙ｆ椂闇€鍦ㄨ姹傚ご鎼哄甫 `X-API-Key`

## 3. 鏋勫缓骞跺惎鍔ㄥ鍣?
瀹夎 Docker 涓?Compose锛堝灏氭湭瀹夎锛屽彲鍙傝€冨畼鏂规枃妗ｏ級銆傚湪椤圭洰鏍圭洰褰曟墽琛岋細

```
docker compose build
docker compose up -d
```

妫€鏌ユ湇鍔★細

```
docker compose ps
curl -fsS http://127.0.0.1:5000/api/health | jq
```

## 4. 閰嶇疆 Nginx 鍙嶅悜浠ｇ悊

Nginx 绔欑偣锛堢ず渚嬶級锛?
```
server {
  listen 80;
  server_name mail.influzzde.top;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  server_name mail.influzzde.top;

  # 璇佷功閰嶇疆锛堝凡绛惧彂锛?  ssl_certificate     /etc/letsencrypt/live/mail.influzzde.top/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/mail.influzzde.top/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

閲嶈浇 Nginx锛歚sudo nginx -t && sudo systemctl reload nginx`

## 5. 鎵撻€?OAuth 鎺堟潈

鍦ㄦ祻瑙堝櫒璁块棶锛堟浛鎹负浣犵殑鍙戜欢浜?Gmail锛夛細

```
https://mail.influzzde.top/oauth/google/authorize?sender_email=your@gmail.com
```

瀹屾垚 Google 鎺堟潈鍚庯紝鍥炶皟鑷筹細

```
https://mail.influzzde.top/oauth/google/callback?code=...
```

鎴愬姛杩斿洖锛歚{"success": true, "email": "your@gmail.com"}`锛屽苟鍦?`token_store/` 涓敓鎴?`token_*.json`銆?
## 6. 鍙戦€佷笌鎺у埗鎺ュ彛锛堢ず渚嬶級

浼犵粺鍙戦€侊紙甯﹂檮浠讹級锛?
```
curl -X POST https://mail.influzzde.top/api/send_emails \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <浣犵殑API_KEY>' \
  -d '{
    "sender_email": "your@gmail.com",
    "excel_file_path": "data.xlsx",
    "subject": "Hello",
    "content": "Hi",
    "attachments": ["product_catalog.pdf"],
    "min_interval": 20,
    "max_interval": 60
  }'
```

妯℃澘鍙戦€侊紙甯﹂檮浠讹級锛?
```
curl -X POST https://mail.influzzde.top/api/send_template_emails \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <浣犵殑API_KEY>' \
  -d '{
    "sender_email": "your@gmail.com",
    "excel_file_path": "data.xlsx",
    "attachments": ["product_catalog.pdf"],
    "min_interval": 20,
    "max_interval": 60
  }'
```

鐘舵€侊細

```
curl https://mail.influzzde.top/api/status
```

鏆傚仠/鎭㈠/鍋滄锛?
```
curl -X POST https://mail.influzzde.top/api/pause  -H 'X-API-Key: <浣犵殑API_KEY>'
curl -X POST https://mail.influzzde.top/api/resume -H 'X-API-Key: <浣犵殑API_KEY>'
curl -X POST https://mail.influzzde.top/api/stop   -H 'X-API-Key: <浣犵殑API_KEY>'
```

## 7. 鐩綍鎸傝浇涓庢枃浠惰鏄?
- `files/`锛氭斁缃檮浠朵笌鍥剧墖锛堝浘鐗囧湪 `files/pics/`锛夈€傚湪妯℃澘 HTML 涓娇鐢?`<img id="logo" />` 寮曠敤瀵瑰簲鏂囦欢鍚嶃€?- `logs/`锛氬簲鐢ㄦ棩蹇楄緭鍑虹洰褰曘€?- `secrets/`锛氫粎鍖呭惈 `credentials.json`锛屼互鍙鏂瑰紡鎸傝浇鍒板鍣?`/secrets`銆?- `token_store/`锛歚token_*.json` 浼氬啓鍒版鐩綍锛屼究浜庢寔涔呭寲銆?
## 8. 鏁呴殰鎺掓煡

- `docker compose logs -f` 鏌ョ湅瀹瑰櫒鏃ュ織銆?- 鎺堟潈鍥炶皟 400锛氭鏌?GCP 鐨勯噸瀹氬悜 URI 鏄惁涓?`.env` 鐨?`OAUTH_REDIRECT_URL` 瀹屽叏涓€鑷达紙鍗忚/鍩熷悕/璺緞锛夈€?- 鍙戦€佸け璐ワ細妫€鏌?Gmail 閰嶉銆乣files/` 鐩綍涓嬬殑闄勪欢鏄惁瀛樺湪銆丒xcel 鍒楁槸鍚︾鍚堣姹傘€?- 鏉冮檺闂锛氬鍣ㄥ `token_store/` 鍜?`logs/` 闇€瑕佸彲鍐欐潈闄愩€?
## 9. Webhook锛圡2锛?
- Webhook 灏嗗湪 M2 瀹炶锛氬彂閫佺敓鍛藉懆鏈熷唴鍚戜綘閰嶇疆鐨?`webhook_url` 鎺ㄩ€?`started/progress/completed/failed` 绛変簨浠讹紝渚夸簬杈句汉绠＄悊绯荤粺瀹炴椂鏇存柊杩涘害銆?- 灞婃椂浼氬湪 OpenAPI 涓柊澧炲瓧娈典笌绔偣璇存槑銆?
## 10. 绀轰緥 .env锛堝彲澶嶅埗涓?.env锛?
鏈湴鑱旇皟锛圵indows/Mac 寮€鍙戠幆澧冿級锛?
```
# 浣跨敤 Web 鎺堟潈锛堟湰鍦板洖璋冿級
AUTH_FLOW=web
GOOGLE_OAUTH_CLIENT_JSON=secrets/credentials.json
OAUTH_REDIRECT_URL=http://127.0.0.1:5000/oauth/google/callback

# API Key锛堣皟鐢ㄥ啓鎺ュ彛闇€鍦ㄨ姹傚ご甯?X-API-Key锛?API_KEY=sk_local_change_me

# MySQL 杩炴帴锛堢ず渚嬶紝鎸変綘鐨勬暟鎹簱淇敼锛?DATABASE_URL=mysql+pymysql://user:pass@127.0.0.1:3306/db?charset=utf8mb4

# 鎺堟潈鍥炶烦鐧藉悕鍗曚笌鍏滃簳
ALLOWED_RETURN_URL_HOSTS=localhost,127.0.0.1
DEFAULT_RETURN_URL=http://127.0.0.1:5000/api/health
ALLOW_DEV_LOCALHOST=true
```

鐢熶骇閮ㄧ讲锛堜簯鏈嶅姟鍣級锛?
```
# 鏈嶅姟鍣ㄤ娇鐢?Web 鎺堟潈
AUTH_FLOW=web
# 鎸囧悜 Web 搴旂敤瀹㈡埛绔殑 JSON锛堝彧璇绘寕杞斤級
GOOGLE_OAUTH_CLIENT_JSON=/opt/email-assistant/secrets/credentials.web.json
# 蹇呴』涓?GCP 鎺у埗鍙颁竴鑷?OAUTH_REDIRECT_URL=https://mail.influzzde.top/oauth/google/callback

# 姝ｅ紡 API Key锛堜笌鍚庡彴涓€鑷达級
API_KEY=sk_live_change_me

# MySQL 杩炴帴锛堟寜浣犵殑瀹為檯搴撳～鍐欙級
# 绀轰緥锛欴ATABASE_URL=mysql+pymysql://root:********@<db-host>:3306/<db>?charset=utf8mb4
DATABASE_URL=mysql+pymysql://user:pass@db-host:3306/prod_db?charset=utf8mb4

# 鎺堟潈鍥炶烦鎺у埗
ALLOWED_RETURN_URL_HOSTS=crm.influzzde.top
DEFAULT_RETURN_URL=https://crm.influzzde.top/oauth/success
ALLOW_DEV_LOCALHOST=false
```

璇存槑锛?- Docker 浼氳嚜鍔ㄨ鍙栧悓鐩綍涓嬬殑 `.env`锛屽苟灏嗗彉閲忔敞鍏ュ鍣ㄣ€?- 鏈湴鐩存帴杩愯鏃讹紝涔熷彲浠ョ敤绯荤粺鐜鍙橀噺瑕嗙洊杩欎簺鍊笺€?- `GOOGLE_OAUTH_CLIENT_JSON` 鎸囧悜浣犱笅杞界殑 GCP OAuth 瀹㈡埛绔?JSON 鏂囦欢锛堢敓浜х敤 Web 搴旂敤瀹㈡埛绔級銆?- `ALLOWED_RETURN_URL_HOSTS` 澶氬煙鍚嶇敤閫楀彿鍒嗛殧锛涙敮鎸佷互鐐瑰紑澶寸殑鍚庣紑鍖归厤锛堝 `.example.com`锛夈€?
