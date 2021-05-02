import requests

import csv
import datetime
import json
import os

class SlackAgentClient(object):
    """
    Class to post messages to slack
    """
    def webhook_post(self, district, message):
        url = os.getenv('SLACK_WEBHOOK_URL')
        text = f"*[Vaccine Slot Alert][{district}]*\n```{message}```"
        payload = {
            "text": text
        }
        requests.request("POST", url, data=json.dumps(payload), headers={}, params={})


class VaccineSlotFinder:

    AGE_LIMIT = 18
    DATE_FORMAT = '%d-%m-%Y'

    PIN_WHITELIST = ['245304']

    DISTRICT_MAP = json.loads(os.getenv('DISTRICT_MAP'))

    DAY_COUNT = 90

    def __init__(self):
        self.base_url = "https://cdn-api.co-vin.in/api/v2"
        self.found = False

    def _process_response(self, response, string):
        center_found = False
        for center in response["centers"]:
            sessions = center["sessions"]
            for session in sessions:
                if session["min_age_limit"] == self.AGE_LIMIT and session["available_capacity"] > 0:
                    center_found = True
                    self.found = True

                    timings = ", ".join(session["slots"])
                    message = f"""
                    Date: {session["date"]}
                    No. of Slots: {session["available_capacity"]}
                    Timings: {timings}
                    Vaccine: {session["vaccine"]}
                    Center Name:    {center["name"]}    
                    Block:  {center["block_name"]}
                    District: {center["district_name"]}
                    Charges: {center["fee_type"]}
                    Pincode: {center["pincode"]}
                    """
                    SlackAgentClient().webhook_post(center["district_name"], message)

        if not center_found:
            print("Not found")
            # SlackAgentClient().webhook_post(f"""Not found for {string}""")

    def controller(self):
        for district in self.DISTRICT_MAP.keys():
            date = None
            for week in range(int(self.DAY_COUNT/7)):
                date = self._get_next_date(date)
                print(f"Checking for district {self.DISTRICT_MAP[district]} on date {date}")
                self.find_by_district(district, date)

            if not self.found:
                SlackAgentClient().webhook_post(f"No Data found for {self.DISTRICT_MAP[district]}")

    def find_by_pincode(self, pincode, date):
        path = "/appointment/sessions/public/calendarByPin"
        url = self.base_url + path
        querystring = {"pincode": pincode, "date": date}

        payload = ""

        response = requests.request("GET", url, data=payload, headers={}, params=querystring)

        response = response.json()

        self._process_response(response, f"{pincode} on {date}")

    def find_by_district(self, district, date):
        path = "/appointment/sessions/public/calendarByDistrict"
        url = self.base_url + path
        querystring = {"district_id": district, "date": date}

        payload = ""

        response = requests.request("GET", url, data=payload, headers={}, params=querystring)

        response = response.json()

        self._process_response(response, f"{self.DISTRICT_MAP[district]} on {date}")

    def print_states_csv(self):
        path= "/admin/location/states"
        url = self.base_url + path

        payload = ""
        response = requests.request("GET", url, data=payload, headers={}, params={})

        response = response.json()
        with open('districts.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["State Name", "State ID", "District Name", "District ID"])

        for res in response["states"]:
            # print(f"""{res["state_name"]},{res["state_id"]}""")
            self._print_districts_csv(res["state_id"], res["state_name"])

    def _print_districts_csv(self, state_id, state_name):
        path = f"/admin/location/districts/{state_id}"
        url = self.base_url + path

        payload = ""
        response = requests.request("GET", url, data=payload, headers={}, params={})

        response = response.json()
        with open('districts.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            for res in response["districts"]:
                # print(f"""{state_name},{state_id},{res["district_name"]},{res["district_id"]}""")
                writer.writerow([state_name, state_id, res["district_name"], res["district_id"]])

    def _get_next_date(self, cur_date=None):
        if cur_date:
            date = datetime.datetime.strptime(cur_date, self.DATE_FORMAT)
            next = date + datetime.timedelta(days=7)
            return next.strftime(self.DATE_FORMAT)

        # Returns default date as today in IST
        return (datetime.datetime.now()+ datetime.timedelta(hours=5,minutes=30)).strftime(self.DATE_FORMAT)

# AWS Lambda invoker
def lambda_handler(event, context):
    VaccineSlotFinder().controller()

# For local testing
if __name__ == "__main__":
    print("here")
    VaccineSlotFinder().controller()
