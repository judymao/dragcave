from json import load
import random

from time import sleep
from datetime import datetime

from bs4 import BeautifulSoup
from robobrowser import RoboBrowser
from openpyxl import load_workbook, Workbook
import lxml

import pandas as pd

# --- Retrieve habitats that are to be searched --- #
HABITAT = {
    'coast': 1,
    'desert': 2,
    'forest': 3,
    'jungle': 4,
    'alpine': 5,
    'volcano': 6
}
habitats = list(HABITAT.keys())

if __name__ == '__main__':
    # --- Retrieve credentials --- #
    try:
        f = open('secrets.json', 'r')
        data = load(f)
        f.close()
        username = data['username']
        password = data['password']
    except Exception as e:
        if type(e) == FileNotFoundError:
            print('ERROR: Secrets.json file not found.')
        else:
            print('ERROR: Failed to retrieve credentials. '
                  + 'Check for syntax errors in your secrets.json.')
        exit(0)

    # --- Retrieve egg descriptions --- #
    EGGS = {}
    try:
        f = open('eggs.txt', 'r', encoding='utf8')
        lines = f.read().splitlines()
        f.close()

        # File must not be empty
        if len(lines) == 0:
            raise Exception('File Empty')
        for i in lines:
            d = i.lower().replace('.', '').strip().split('=')
            # Append to dictionary with the description as entry
            EGGS[d[0]] = d[1]

    except Exception as e:
        if type(e) == FileNotFoundError:
            print('ERROR: eggs.txt file not found.')
        else:
            print('ERROR:', e)
        exit(0)

    # --- Authentication --- #
    try:
        browser = RoboBrowser(parser='html.parser')
        browser.open('https://dragcave.net/')
        form = browser.get_form()
        form['username'] = username
        form['password'] = password
        browser.submit_form(form)
        print("-- SUCCESSFUL AUTHENTICATION --")

    except:
        print('Failed to authenticate. Check your credentials or Dragon Cave status')
        exit(0)

    # --- Initialization --- #
    biomes = {}
    stats = {}

    print('-- INITIALIZING TRACKER --')
    for h in habitats:
        # Initialize biomes
        biomes[h] = []
        stats[h] = {}

        # Open and parse habitat
        browser.open('https://dragcave.net/locations/' + str(HABITAT[h]))
        soup = BeautifulSoup(str(browser.parsed()), features='html.parser')
        cave = (soup.find('div', class_='eggs')).findAll('div')

        # Search available egg(s) in current habitat.
        for egg in cave:
            eggCode = egg.find('a').get('href')[-5:]
            eggDesc = egg.find('span').text.lower().replace('.', '')

            if eggDesc in EGGS:
                breed = EGGS[eggDesc]
            else:
                breed = 'other'

            # Update biomes and stats
            biomes[h].append(eggCode)

            if breed not in stats[h]:
                stats[h][breed] = 0

            stats[h][breed] += 1

    # --- Execution --- #
    print('-- RUNNING TRACKER --')
    # Runs while for a set amt of time
    run_length = 5  # Number of hours to run
    start_hr = datetime.now().hour
    remaining_time = run_length
    filename = f'results/{datetime.now().date()}_dc-stats_starthr-{start_hr}_runlen-{run_length}.xlsx'

    print(f'Started at {datetime.now()}. Running for {run_length} hour(s).')

    while remaining_time > 0:
        for h in habitats:
            # Open and parse habitat
            try:
                browser.open('https://dragcave.net/locations/' + str(HABITAT[h]))
                soup = BeautifulSoup(str(browser.parsed()), features='html.parser')
                if soup.find('div', class_='eggs') is None:
                    print(f"Soup not found {datetime.now()}.")
                    break

                cave = soup.find('div', class_='eggs').findAll('div')

                codeList = []
                hour = datetime.now().hour

                # Search available egg(s) in current habitat.
                for egg in cave:
                    eggCode = egg.find('a').get('href')[-5:]
                    eggDesc = egg.find('span').text.lower().replace('.', '')

                    codeList.append(eggCode)

                    if eggCode not in biomes[h]:

                        if eggDesc in EGGS:
                            breed = EGGS[eggDesc]
                        else:
                            breed = 'other'

                        if breed in ('gold', 'silver', 'staterae'):
                            print(f'------ {breed} ({eggCode}) found in {h} @ {datetime.now()} ------')

                        if breed not in stats[h]:
                            stats[h][breed] = 0

                        stats[h][breed] += 1

                # Update biomes
                biomes[h] = codeList

            except Exception as e:
                print("Error encountered:", e)
                print("Time remaining:", remaining_time)
                pass

        hrs_elapsed = datetime.now().hour - start_hr
        if remaining_time + hrs_elapsed > run_length:
            remaining_time = run_length - hrs_elapsed
            stats_df = pd.DataFrame.from_dict({i: stats[i] for i in stats.keys()}, orient='index').T

            if hrs_elapsed == 1:
                writer = pd.ExcelWriter(filename, engine='xlsxwriter')

            if hrs_elapsed == 2:
                writer = pd.ExcelWriter(filename, engine='openpyxl', mode='a')
                # file should now exist (created when hrs_elapsed == 1)
                book = load_workbook(filename)
                writer.book = book

            stats_df.to_excel(writer, sheet_name=str(start_hr + hrs_elapsed - 1))

            writer.save()

            # Reset statistics
            for h in habitats:
                stats[h] = {}
            print(f'{hrs_elapsed} hour(s) have passed. {remaining_time} hour(s) left. Current stats have been saved at {datetime.now()}.')

        sleep(0.1)
    writer.close()
    print(f'-- EXECUTION FINISHED IN {run_length} HOUR(S) --')
    exit(0)
