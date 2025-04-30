import datetime
import shutil
import subprocess
import json
import os
import time
from typing import Dict, List
from schedule import Scheduler

import requests
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker


NUM_BOULDERS = 40
# category_mapping = {"10": "male", "11": "female"}
name_mapping = {"BLOC house:": "blockhouse", "Boulderclub:": "boulderclub", "Newton:": "newton"}


def get_participants(male: bool) -> List[str]:
    if male:
        url = "https://boulder-top.com/ranking-xmlhttp_loadRanking.php?GTyp=2&CID=53&VID=42&REid=67&KLid=152&RankingTyp=1&REBez=Graz&KLBez=M%C3%A4nner&HAID="
    else:
        url = "https://boulder-top.com/ranking-xmlhttp_loadRanking.php?GTyp=2&CID=53&VID=42&REid=67&KLid=153&RankingTyp=1&REBez=Graz&KLBez=Frauen&HAID="
    text = requests.get(url).json()["Return_DIV_Body"]
    participants = []
    for e in text.split('<div class="ranking-text"><span class="ranking-left">')[1:]:
        participants.append(e.split('id="s-')[1].split('"')[0].split("-")[-1])
    print(male, len(participants))
    return participants


def get_boulders(participant: str, male: bool) -> Dict[str, int]:
    text = requests.get(f'https://boulder-top.com/comp/bss25/page/boulder-eintragen/t={participant}&k={152 if male else 153}&r=67&v=42&c=53&h=').text
    boulders = {}
    for location, location_name in name_mapping.items():
        relevant = text.split(location)
        if len(relevant) < 2:
            boulders[location_name] = [0] * NUM_BOULDERS
        else:
            parts = relevant[1].lower().split('https://boulder-top.com/assets/img/bss25/co_icon_bouldereintragen_')[1:NUM_BOULDERS+1]
            boulders[location_name] = [0 if p[0] == "n" else 1 for p in parts]
    return boulders

def load_data(male: bool) -> Dict[str, Dict[str, int]]:
    participants = get_participants(male)
    boulders_per_participant = {}
    for p in participants:
        boulders_per_participant[p] = get_boulders(p, male)
    return boulders_per_participant


def gen_stats():
    date = datetime.datetime.now()
    print("Generating stats for", date.strftime("%Y-%m-%d"))
    fn = date.strftime("%Y-%m-%d.json")
    if os.path.exists(fn):
        print("Using existing data")
        with open(date.strftime("%Y-%m-%d.json")) as f:
            data = json.load(f)
    else:
        data = {"male": load_data(True), "female": load_data(False)}
        with open(date.strftime("%Y-%m-%d.json"), 'w') as f:
            json.dump(data, f)

    old_fn = (date - datetime.timedelta(days=1)).strftime("%Y-%m-%d.json")
    if os.path.exists(old_fn):
        data_old = json.load(open(old_fn))
    else:
        data_old = data


    def stats(datas):
        blochouse = {i+1: [0]*9 for i in range(NUM_BOULDERS)}
        boulderclub = {i+1: [0]*9 for i in range(NUM_BOULDERS)}
        newton = {i+1: [0]*9 for i in range(NUM_BOULDERS)}

        for category, dat in datas.items():
            c = 3 if category == "female" else 2
            for link, d in dat.items():
                for h, vs in d.items():
                    if sum(vs) == 0:
                        continue
                    res = blochouse if "bloc" in h else (boulderclub if "bould" in h else newton)
                    for i, v in enumerate(vs):
                        if v:
                            res[i+1][0] += 1
                            res[i+1][(int(c)-1)*3] += 1
                        res[i+1][1] += 1
                        res[i+1][(int(c)-1)*3+1] += 1
                    for i in range(1, NUM_BOULDERS+1):
                        if sum(vs) >= i:
                            res[i][2] += 1
                            res[i][(int(c)-1)*3+2] += 1

        return blochouse, boulderclub, newton


    blochouse_new, boulderclub_new, newton_new = stats(data)
    blochouse_old, boulderclub_old, newton_old = stats(data_old)


    def format_percent(percent):
        s = "#" * percent + " " * (100 - percent)
        return "|".join(s[i:i+25] for i in range(0, 100, 25))


    def subplot(data, data_old, idx, pos, name, fig):
        ax = fig.add_subplot(3, 3, pos)
        ax.set_title(name + " absolut")
        X_axis = np.arange(NUM_BOULDERS)
        data_sorted = {k: v for k, v in sorted(data.items(), reverse=True, key=lambda x: x[1][idx])}
        data_sorted_old = {k: data_old[k] for k in data_sorted.keys()}
        plt.bar(X_axis - 0.2, [(v[idx]) for v in data_sorted.values()], width=0.4, label="new", color=(0.0, 0.6, 0.0))
        plt.bar(X_axis + 0.2, [(v[idx]) for v in data_sorted_old.values()], width=0.4, label="old", color=(1.0, 0.4, 0.4))
        plt.grid(axis="y")
        ax.set(xticks=X_axis, xticklabels=[str(x) for x in data_sorted.keys()])
        ax.xaxis.set_minor_formatter(ticker.FixedFormatter([str(x) for i, x in enumerate(data_sorted.keys()) if i % 5 != 0]))
        ax.xaxis.set_major_formatter(ticker.FixedFormatter([str(x) for i, x in enumerate(data_sorted.keys()) if i % 5 == 0]))
        ax.set_xticks(list(range(0, NUM_BOULDERS, 5)))
        ax.set_xticks(list(range(NUM_BOULDERS)), minor=True)
        ax.legend()
        plt.grid(axis="x")

        ax = fig.add_subplot(3, 3, pos+1)
        ax.set_title(name + " relativ")
        X_axis = np.arange(NUM_BOULDERS)
        data_sorted = {k: v for k, v in sorted(data.items(), reverse=True, key=lambda x: x[1][idx])}
        data_sorted_old = {k: data_old[k] for k in data_sorted.keys()}
        plt.bar(X_axis - 0.2, [(v[idx]*100/max(1,v[idx+1])) for v in data_sorted.values()], width=0.4, label="new", color=(0.0, 0.6, 0.0))
        plt.bar(X_axis + 0.2, [(v[idx]*100/max(1,v[idx+1])) for v in data_sorted_old.values()], width=0.4, label="old", color=(1.0, 0.4, 0.4))
        plt.grid(axis="y")
        ax.set(xticks=X_axis, xticklabels=[str(x) for x in data_sorted.keys()])
        ax.xaxis.set_minor_formatter(ticker.FixedFormatter([str(x) for i, x in enumerate(data_sorted.keys()) if i % 5 != 0]))
        ax.xaxis.set_major_formatter(ticker.FixedFormatter([str(x) for i, x in enumerate(data_sorted.keys()) if i % 5 == 0]))
        ax.set_xticks(list(range(0, NUM_BOULDERS, 5)))
        ax.set_xticks(list(range(NUM_BOULDERS)), minor=True)
        ax.legend()
        plt.grid(axis="x")

        ax = fig.add_subplot(3, 3, pos+2)
        ax.set_title(name + " Anzahl")
        X_axis = np.arange(NUM_BOULDERS)
        plt.bar(X_axis - 0.2, [(v[idx+2]*100/max(1,v[idx+1])) for v in data.values()], width=0.4, label="new", color=(0.0, 0.6, 0.0))
        plt.bar(X_axis + 0.2, [(v[idx+2]*100/max(1,v[idx+1])) for v in data_old.values()], width=0.4, label="old", color=(1.0, 0.4, 0.4))
        ax.set_yticks(list(range(0, 100, 10)))
        ax.set(xticks=X_axis, xticklabels=[str(x) for x in range(1, NUM_BOULDERS+1)])
        ax.legend()
        plt.grid(axis="y")


    def plot(data, data_old, name):
        fig = plt.figure(figsize=(NUM_BOULDERS, 15))
        fig.tight_layout()
        fig.suptitle(name, fontsize=32)
        subplot(data, data_old, 0, 1, "alle", fig)
        subplot(data, data_old, 3, 4, "männlich", fig)
        subplot(data, data_old, 6, 7, "weiblich", fig)
        plt.savefig(date.strftime("/app/blocsummer/%Y-%m-%d/%Y-%m-%d_") + name + ".png", bbox_inches='tight')

    os.makedirs(date.strftime("/app/blocsummer/%Y-%m-%d"), exist_ok=True)
    shutil.copyfile(fn, date.strftime("/app/blocsummer/%Y-%m-%d/") + fn)
    plot(newton_new, newton_old, "newton")
    plot(blochouse_new, blochouse_old, "blochouse")
    plot(boulderclub_new, boulderclub_old, "boulderclub")
    subprocess.run(["./git.sh"])


if __name__ == "__main__":
    gen_stats()
    scheduler = Scheduler()
    scheduler.every().day.at("03:00").do(gen_stats)
    while True:
        scheduler.run_pending()
        time.sleep(600)
