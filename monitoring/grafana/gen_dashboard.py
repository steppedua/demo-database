"""Генератор единственного дашборда доклада: python3 monitoring/grafana/gen_dashboard.py

Один экран, читается сверху вниз:
  1. четыре цифры: очередь к пулу, idle in transaction, возраст транзакции, отказы;
  2. одно и то же соединение с двух сторон: пул HikariCP (приложение) и pg_stat_activity (база);
  3. последствия: сколько ждут соединение, сколько его держат, отказы;
  4. таблица «что висит в базе прямо сейчас»;
  5. ниже экрана — технические метрики: приложение (CPU, память, потоки Tomcat и JVM, HTTP)
     и Postgres (CPU и память контейнера, диск, TPS, соединения, кэш, блокировки).
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboards", "tx.json")
DS = {"type": "prometheus", "uid": "prometheus"}
BLUE, GRAY, ORANGE, RED, GREEN, PURPLE, AMBER = "#3274D9", "#8e8e8e", "#FF9830", "#E02F44", "#56A64B", "#A352CC", "#EAB839"
APP = 'application_name="demo-database"'   # только соединения приложения, без экспортера и psql

panels, y = [], 0


def target(expr, legend="", ref="A", instant=False, fmt=None):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    t.update({"instant": True, "range": False} if instant else {"range": True})
    if fmt:
        t["format"] = fmt
    return t


def add(panel, x, w, h):
    panel.update({"id": len(panels) + 1, "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h}})
    panels.append(panel)


def text(md, h):
    global y
    panels.append({"id": len(panels) + 1, "type": "text", "title": "", "gridPos": {"x": 0, "y": y, "w": 24, "h": h},
                   "options": {"mode": "markdown", "content": md}})
    y += h


def row(title):
    global y
    panels.append({"id": len(panels) + 1, "type": "row", "title": title, "collapsed": False, "panels": [],
                   "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}})
    y += 1


def stat(title, expr, unit, steps, x, desc, w=4, h=4):
    add({"type": "stat", "title": title, "description": desc, "targets": [target(expr, title)],
         "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "background",
                     "graphMode": "area", "textMode": "value", "justifyMode": "center"},
         "fieldConfig": {"defaults": {"unit": unit, "decimals": 0,
                                      "thresholds": {"mode": "absolute",
                                                     "steps": [{"color": c, "value": v} for v, c in steps]}},
                         "overrides": []}}, x, w, h)


def ts(title, series, unit, x, w, desc, h=8, fill=10):
    """series: (expr, legend, color[, "dashed" | "right"])"""
    targets, overrides = [], []
    for i, (expr, legend, color, *rest) in enumerate(series):
        ref = chr(65 + i)
        targets.append(target(expr, legend, ref))
        props = [{"id": "color", "value": {"mode": "fixed", "fixedColor": color}}]
        if "dashed" in rest:
            props += [{"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [8, 6]}},
                      {"id": "custom.fillOpacity", "value": 0}]
        if "right" in rest:   # своя шкала справа, чтобы большая очередь не сплющила остальные линии
            props += [{"id": "custom.axisPlacement", "value": "right"},
                      {"id": "custom.axisLabel", "value": legend.split(" — ")[0]}]
        overrides.append({"matcher": {"id": "byFrameRefID", "options": ref}, "properties": props})
    add({"type": "timeseries", "title": title, "description": desc, "targets": targets,
         "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                     "tooltip": {"mode": "multi", "sort": "desc"}},
         "fieldConfig": {"defaults": {"unit": unit, "min": 0,
                                      "custom": {"lineWidth": 2, "fillOpacity": fill, "showPoints": "never",
                                                 "spanNulls": True}},
                         "overrides": overrides}}, x, w, h)


# ---------------------------------------------------------------------------------------------
text("**Куда смотреть, сверху вниз.** 1) `Ждут соединение` > 0 — пул исчерпан. "
     "2) Слева `active` упёрся в пунктир max, справа те же соединения в Postgres — оранжевые `idle in transaction`: "
     "транзакция открыта, а приложение занято другим. 3) `Самая старая транзакция` растёт, а запросов в базе нет (`active` ≈ 0) — "
     "виноват код, а не база. 4) Таблица внизу — какие сессии и с каким последним запросом.", 2)

stat("Ждут соединение", "max(hikaricp_connections_pending) or vector(0)", "short",
     [(None, GREEN), (1, AMBER), (10, RED)], 0, "Потоки в очереди к пулу (hikaricp_connections_pending)", w=6)
stat("Idle in transaction", 'sum(pg_sessions_count{state=~"idle in transaction.*"}) or vector(0)', "short",
     [(None, GREEN), (1, AMBER), (5, RED)], 6, "Транзакция открыта, база ждёт команду, а приложение занято другим", w=6)
stat("Самая старая транзакция", "floor(max(pg_sessions_max_xact_age_seconds)) or vector(0)", "s",
     [(None, GREEN), (5, AMBER), (15, RED)], 12, "now() - xact_start", w=6)
stat("Отказы пула за 5 мин", "sum(increase(hikaricp_connections_timeout_total[5m])) or vector(0)", "short",
     [(None, GREEN), (1, RED)], 18, "Connection is not available, request timed out after 30000ms", w=6)
y += 4

ts("Пул HikariCP — приложение", [
    ("max(hikaricp_connections_active)", "active — выданы потокам", BLUE),
    ("max(hikaricp_connections_idle)", "idle — свободны", GREEN),
    ("max(hikaricp_connections_pending)", "pending — ждут соединение", ORANGE),
    ("max(hikaricp_connections_max)", "maximum-pool-size", GRAY, "dashed")],
    "short", 0, 12, "Пул исчерпан, когда active упёрся в пунктир max, а pending > 0.", h=9, fill=15)
ts("Те же соединения в Postgres — pg_stat_activity", [
    (f'sum(pg_sessions_count{{{APP}, state="idle"}}) or vector(0)', "idle — свободное соединение пула (норма)", GREEN),
    (f'sum(pg_sessions_count{{{APP}, state="active"}}) or vector(0)', "active — выполняет запрос", BLUE),
    (f'sum(pg_sessions_count{{{APP}, state=~"idle in transaction.*"}}) or vector(0)', "idle in transaction", ORANGE)],
    "short", 12, 12, "Сессии с application_name=demo-database. idle — норма, idle in transaction — проблема.", h=9, fill=15)
y += 9

ts("Сколько поток ждёт соединение", [
    ("max(hikaricp_connections_acquire_seconds_max)", "max", ORANGE)],
    "s", 0, 8, "Упирается в connection-timeout (30 с) — и запрос падает. "
               "Micrometer помнит max ещё ~2 мин после нагрузки.", fill=0)
ts("Сколько соединение занято (≈ длина транзакции)", [
    ("max(hikaricp_connections_usage_seconds_max)", "max", PURPLE)],
    "s", 8, 8, "От getConnection() до close(). В норме — миллисекунды; в кейсе — вся медленная работа, 20 с.", fill=0)
ts("Отказы пула за 30 с", [
    ("sum(increase(hikaricp_connections_timeout_total[30s])) or vector(0)", "Connection is not available", RED)],
    "short", 16, 8, "Запросы, не дождавшиеся соединения за connection-timeout: пользователь получил 500. "
                    "Счётчик Hikari есть с нуля, поэтому первые отказы не теряются (у http_server_requests "
                    "серия status=500 появляется сразу со значением, и rate её первую порцию не видит).", fill=20)
y += 8

exclude = {k: True for k in ["Time", "__name__", "server", "instance", "job"]}
rename = {"pid": "pid", "application_name": "приложение", "state": "state", "wait_event_type": "ждёт",
          "query": "последний запрос", "Value": "возраст транзакции"}
add({"type": "table", "title": "Что висит в базе прямо сейчас (транзакции старше 1 с)",
     "description": "Топ-10 из pg_stat_activity. Кандидаты на pg_terminate_backend(pid).",
     "targets": [target("pg_oldest_xact_age_seconds", instant=True, fmt="table")],
     "transformations": [{"id": "organize", "options": {
         "excludeByName": exclude, "renameByName": rename,
         "indexByName": {k: i for i, k in enumerate(rename)}}}],
     "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False},
                 "sortBy": [{"displayName": "возраст транзакции", "desc": True}]},
     "fieldConfig": {"defaults": {"noValue": "Ничего не висит"},
                     "overrides": [{"matcher": {"id": "byName", "options": "возраст транзакции"}, "properties": [
                         {"id": "unit", "value": "s"}, {"id": "decimals", "value": 0},
                         {"id": "custom.cellOptions", "value": {"type": "color-background", "mode": "basic"}},
                         {"id": "thresholds", "value": {"mode": "absolute", "steps": [
                             {"color": GREEN, "value": None}, {"color": AMBER, "value": 5},
                             {"color": RED, "value": 30}]}}]}]}}, 0, 24, 8)
y += 8

# ---------------------------------------------------------------------------------------------
APP_JOB = 'job="demo-database"'
row("Приложение: CPU, память, потоки")
ts("CPU приложения", [
    (f"max(process_cpu_usage{{{APP_JOB}}})", "процесс JVM", BLUE),
    (f"max(system_cpu_usage{{{APP_JOB}}})", "вся машина", GRAY, "dashed")],
    "percentunit", 0, 8, "Доля всех ядер (system_cpu_count). В кейсе пул пуст, а CPU низкий: потоки не работают, а ждут.")
ts("Пул потоков Tomcat", [
    ("max(tomcat_threads_busy_threads)", "busy — обрабатывают запрос", ORANGE),
    ("max(tomcat_threads_current_threads)", "current — созданы", BLUE),
    ("max(tomcat_threads_config_max_threads)", "server.tomcat.threads.max", GRAY, "dashed")],
    "short", 8, 8, "busy упёрся в max — новые запросы ждут в очереди коннектора. В кейсе busy растёт, "
                   "пока потоки стоят в очереди к Hikari. Нужен server.tomcat.mbeanregistry.enabled: true.")
ts("HTTP-запросы в секунду", [
    (f'sum(rate(http_server_requests_seconds_count{{{APP_JOB}, status=~"[23].."}}[30s])) or vector(0)', "2xx/3xx", GREEN),
    (f'sum(rate(http_server_requests_seconds_count{{{APP_JOB}, status=~"4.."}}[30s])) or vector(0)', "4xx", AMBER),
    (f'sum(rate(http_server_requests_seconds_count{{{APP_JOB}, status=~"5.."}}[30s])) or vector(0)', "5xx", RED)],
    "reqps", 16, 8, "http_server_requests по статусу. 5xx в кейсе — Connection is not available.")
y += 8

ts("Время ответа HTTP", [
    (f"sum(rate(http_server_requests_seconds_sum{{{APP_JOB}}}[30s])) / sum(rate(http_server_requests_seconds_count{{{APP_JOB}}}[30s]))",
     "среднее", BLUE),
    (f"max(http_server_requests_seconds_max{{{APP_JOB}}})", "max", ORANGE)],
    "s", 0, 8, "Без гистограмм есть только среднее и max. В кейсе max упирается в connection-timeout.", fill=0)
ts("Память JVM (heap)", [
    (f'sum(jvm_memory_used_bytes{{{APP_JOB}, area="heap"}})', "used", BLUE),
    (f'sum(jvm_memory_committed_bytes{{{APP_JOB}, area="heap"}})', "committed", GREEN)],
    "bytes", 8, 8, "used пилой — норма. used не падает после GC и растёт к -Xmx — утечка, следом OutOfMemoryError. "
                   "-Xmx на графике нет: на стенде это дефолтная четверть RAM ноутбука, он сплющил бы линии.")
ts("Потоки JVM по состояниям", [
    (f'max(jvm_threads_states_threads{{{APP_JOB}, state="runnable"}})', "runnable", GREEN),
    (f'max(jvm_threads_states_threads{{{APP_JOB}, state="timed-waiting"}})', "timed-waiting", ORANGE),
    (f'max(jvm_threads_states_threads{{{APP_JOB}, state="waiting"}})', "waiting", BLUE),
    (f'max(jvm_threads_states_threads{{{APP_JOB}, state="blocked"}})', "blocked — ждут synchronized", RED)],
    "short", 16, 8, "Поток в очереди к Hikari — timed-waiting (ждёт не дольше connection-timeout). "
                    "Рост blocked — конкуренция за монитор в коде. Кто именно ждёт — thread dump.")
y += 8

# ---------------------------------------------------------------------------------------------
DB = 'datname="demo_database"'
row("Postgres: ресурсы и нагрузка")
ts("CPU контейнера Postgres", [
    ("rate(pg_container_cpu_seconds_total[30s])", "ядер занято", BLUE),
    ("rate(pg_container_cpu_throttled_seconds_total[30s])", "throttled — упёрлись в CPU-лимит", RED)],
    "short", 0, 8, "Все backend'ы и служебные процессы, из cgroup контейнера (pg_container в queries.yaml). "
                   "1 = одно ядро целиком. В кейсе ≈ 0: пул исчерпан, а база простаивает.")
ts("Память контейнера Postgres", [
    ("max(pg_container_memory_working_set_bytes)", "working set — по нему OOM killer", BLUE),
    ("max(pg_container_memory_usage_bytes)", "usage с page cache", GREEN),
    ("max(pg_container_memory_limit_bytes)", "mem_limit", GRAY, "dashed")],
    "bytes", 8, 8, "working set дошёл до лимита — контейнер убьёт OOM killer, Postgres перезапустит все backend'ы. "
                   "Page cache сверх working set ядро отдаёт само.")
ts("Диск контейнера Postgres", [
    ("rate(pg_container_io_read_bytes_total[30s])", "чтение", BLUE),
    ("rate(pg_container_io_write_bytes_total[30s])", "запись", ORANGE)],
    "Bps", 16, 8, "io.stat cgroup: реальные чтения с диска, мимо shared_buffers и page cache.", fill=0)
y += 8

ts("Транзакции в секунду", [
    (f"sum(rate(pg_stat_database_xact_commit{{{DB}}}[30s]))", "commit", GREEN),
    (f"sum(rate(pg_stat_database_xact_rollback{{{DB}}}[30s]))", "rollback", RED)],
    "short", 0, 8, "pg_stat_database. Всплеск rollback — ошибки, дедлоки или таймауты в приложении.")
ts("Соединения к базе", [
    ("sum(pg_stat_database_numbackends)", "все backend'ы", BLUE),
    (f"sum(pg_sessions_count{{{APP}}}) or vector(0)", "приложение", GREEN),
    ("max(pg_settings_max_connections)", "max_connections", GRAY, "dashed")],
    "short", 8, 8, "Упёрлись в пунктир — FATAL: sorry, too many clients already. "
                   "Последние superuser_reserved_connections (3) достаются только суперпользователю.")
ts("Попадание в кэш (shared_buffers)", [
    (f"sum(rate(pg_stat_database_blks_hit{{{DB}}}[1m])) / "
     f"(sum(rate(pg_stat_database_blks_hit{{{DB}}}[1m])) + sum(rate(pg_stat_database_blks_read{{{DB}}}[1m])))",
     "hit ratio", GREEN)],
    "percentunit", 16, 8, "Доля страниц из shared_buffers. Для OLTP норма > 99 %. "
                          "blks_read может прийти из page cache ОС, а не с диска — сверяйте с диском контейнера.", fill=0)
y += 8

ts("Блокировки по режимам", [
    (f'sum(pg_locks_count{{{DB}, mode="accesssharelock"}})', "AccessShare — SELECT", GREEN),
    (f'sum(pg_locks_count{{{DB}, mode="rowexclusivelock"}})', "RowExclusive — INSERT/UPDATE/DELETE", BLUE),
    (f'sum(pg_locks_count{{{DB}, mode="sharelock"}})', "Share — ожидание чужой транзакции", ORANGE),
    (f'sum(pg_locks_count{{{DB}, mode="accessexclusivelock"}})', "AccessExclusive — DDL", RED)],
    "short", 0, 8, "pg_locks: и выданные, и ожидающие. AccessExclusive дольше секунды — DDL держит таблицу, "
                   "Share растёт — сессии ждут строки, занятые другой транзакцией.", fill=0)
ts("Строки в секунду", [
    (f"sum(rate(pg_stat_database_tup_fetched{{{DB}}}[30s]))", "fetched — по индексу", BLUE),
    (f"sum(rate(pg_stat_database_tup_returned{{{DB}}}[30s]))", "returned — просмотрено", GRAY),
    (f"sum(rate(pg_stat_database_tup_updated{{{DB}}}[30s]))", "updated", ORANGE),
    (f"sum(rate(pg_stat_database_tup_inserted{{{DB}}}[30s]))", "inserted", GREEN),
    (f"sum(rate(pg_stat_database_tup_deleted{{{DB}}}[30s]))", "deleted", RED)],
    "short", 8, 8, "returned намного больше fetched — запросы читают лишнее, ищите seq scan в pg_stat_statements.", fill=0)
ts("Дедлоки и временные файлы за минуту", [
    (f"sum(increase(pg_stat_database_deadlocks{{{DB}}}[1m])) or vector(0)", "дедлоки (40P01)", RED),
    (f"sum(increase(pg_stat_database_temp_files{{{DB}}}[1m])) or vector(0)", "temp-файлы — не хватило work_mem", AMBER)],
    "short", 16, 8, "Разовый дедлок — норма, рост — строки блокируются в разном порядке. "
                    "Подробности обоих — в логе Postgres (deadlock detected, log_temp_files=0).", fill=20)

dash = {"uid": "tx", "title": "Транзакции и пул соединений",
        "description": "Застывшие транзакции: один кейс, cases/tx/README.md",
        "tags": ["talk-tx"], "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True,
        "refresh": "5s", "time": {"from": "now-5m", "to": "now"}, "graphTooltip": 1,
        "timepicker": {"refresh_intervals": ["2s", "5s", "10s", "30s"]},
        "annotations": {"list": [
            {"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True,
             "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"},
            {"datasource": DS, "enable": False, "name": "Алерты", "iconColor": RED,
             "expr": 'ALERTS{alertstate="firing"}', "step": "10s", "titleFormat": "{{alertname}}",
             "textFormat": "{{severity}}", "useValueForTime": False}]},
        "panels": panels, "templating": {"list": []}}

with open(OUT, "w") as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)
print(f"{OUT}: {len(panels)} панелей")
