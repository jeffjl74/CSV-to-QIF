'''**************************************************************************/
#
#    @file    CSV_to_QIF.py
#    @author   Mario Avenoso (M-tech Creations)
#    @license  MIT (see license.txt)
#
#    Program to convert from a CSV to a QIF file using a definitions
#    to describe how the CSV is formatted
#
#    @section  HISTORY
#    v0.2 - Added payee ignore option  1/18/2016 feature update
#    v0.1 - First release 1/1/2016 beta release
#
'''#**************************************************************************/


from datetime import datetime
from io import StringIO
import locale
import os
import sys
import re
import csv
import json

class ColumnMap:
    def __init__(self, deff_):
        upperffset = ord("A")
        loweroffset =  ord("a")
        csvdeff = json.load(deff_)

        # time formats @ https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
        for key,val in csvdeff.items():
            if isinstance(val, str) and val.isalpha() and len(val) == 1:
                 # column index
                if val.isupper():
                    val = ord(val) - upperffset
                else:
                    val = ord(val) - loweroffset
            self.__dict__[key] = val

        # set some defaults
        if self.__dict__.get("accountType", None) is None:
            self.accountType = "Bank"
        if self.__dict__.get("Separator", None) is None:
            self.Separator = ","
        if self.__dict__.get("StartLine", None) is None:
            self.StartLine = 1
        if self.__dict__.get("QifTimeFormat", None) is None:
            self.QifTimeFormat = "%y/%m/%d"


class BankRecord:
    def __init__(self):
        self.order = ['date', 'amount', 'cleared', 'num', 'payee', 'memo', 'address', 'category', 'categoryInSplit', 'memoInSplit', 'amountOfSplit']
        self.ids =   ['D',    'T',      'C',       'N',   'P',     'M',    'A',       'L',        'S',               'E',           '$',           ]
        self.date = None
        self.amount = None
        self.cleared = None
        self.num = None
        self.payee = None
        self.memo = None
        self.address = None
        self.category = None
        self.categoryInSplit = None
        self.memoInSplit = None
        self.amountOfSplit = None

    def get_formatted_string(self):
        result = ""
        for attr, id_char in zip(self.order, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n"

class InvstRecord:
    def __init__(self, row=None, map=None):
        self.order = ['date', 'action', 'security', 'price', 'quantity', 'cleared', 'transfer_text', 'memo', 'commission', 'category', 'amountT', 'amountU', 'amount_transferred']
        self.ids =   ['D',    'N',      'Y',        'I',     'Q',        'C',       'P',             'M',    'O',          'L',        'T',       'U',       '$']

        self.date_in =  datetime.strptime(row[map.date], map.CsvTimeFormat) \
                        if row and map \
                        and getattr(map,"date",None) is not None \
                        else None
        self.date = datetime.strftime(self.date_in, map.QifTimeFormat) \
                    if self.date_in is not None \
                    else None
        
        self.security = row[map.security] if row and map \
                        and getattr(map,"security",None) is not None \
                        and len(row[map.security]) > 0 \
                        else None
        self.memo = row[map.memo] if row and map \
                    and getattr(map,"memo",None) is not None \
                    and len(row[map.memo]) > 0 \
                    else None
        self.action =   row[map.action] if row and map \
                        and getattr(map,"action",None) is not None \
                        and len(row[map.action]) > 0 \
                        else None
        # translate action to QIF terms?
        if self.action is not None:
            self.valmap = getattr(map,"ActionMap",None)
            if self.valmap is not None:
                if self.action in self.valmap:
                    if self.valmap[self.action] == 'prompt':
                        print (self.date, self.action, self.memo)
                        self.action = input ("Enter a QIF ID 'N' Action for the record above: ")
                    else:
                        self.action = self.valmap[self.action]

        self.price =    abs(locale.atof(row[map.price])) if row and map \
                        and getattr(map,"price",None) is not None \
                        and len(row[map.price]) > 0 \
                        else None
        self.quantity = locale.atof(row[map.quantity]) \
                        if row and map and getattr(map,"quantity",None) is not None \
                        and len(row[map.quantity]) > 0 \
                        and int(row[map.quantity]) > 0 \
                        else None
        self.cleared =  row[map.cleard] if row and map \
                        and getattr(map,"cleared",None) is not None \
                        and len(row[map.cleared]) > 0 \
                        else None
        self.transfer_text = row[map.transfer_text] if row and map \
                            and getattr(map,"transfer_text",None) is not None \
                            and len(row[map.transfer_text]) > 0 \
                            else None
        self.commission =   locale.atof(row[map.commission]) if row and map \
                            and getattr(map,"commission",None) is not None \
                            and len(row[map.commission]) > 0 \
                            and is_float(row[map.commission]) \
                            else None
        self.category = row[map.category] if row and map and \
                        getattr(map,"category",None) is not None \
                        and len(row[map.category]) > 0 \
                        else None
        self.amountT =  row[map.amountT] if row and map \
                        and getattr(map,"amountT",None) is not None \
                        and len(row[map.amountT]) > 0 \
                        else None
        self.amountU =  row[map.amountU] if row and map \
                        and getattr(map,"amountU",None) is not None \
                        and len(row[map.amountU]) > 0 \
                        else None
        self.amount_transferred =   row[map.amount_transferred] if row and map \
                                    and getattr(map,"amount_transferred",None) is not None \
                                    and len(row[map.amount_transferred]) > 0 \
                                    else None

        # extra columns that are not part of a QIF record but we want to capture
        self.Fees = locale.atof(row[map.Fees]) if row and map \
                    and getattr(map,"Fees",None) is not None \
                    and len(row[map.Fees]) > 0 \
                    else None
        self.Multiplier =   int(row[map.Multiplier]) if row and map \
                            and getattr(map,"Multiplier",None) is not None \
                            and len(row[map.Multiplier]) > 0 \
                            else 1

        # any caluculated fields?
        valmap = getattr(map, "CalculationRules", None)
        if valmap is not None:
            for attr in valmap:
                if getattr(self, attr, None) is not None:
                    # we have a calculation
                    expr = valmap[attr]
                    self.caluculate_field(expr)

        # change the sign on anything?
        valmap = getattr(map, "InvertRules", None)
        if valmap is not None:
            # we have invert rules
            # do we have the attribute(s) it wants to invert?
            for attr in valmap:
                if getattr(self, attr, None) is not None:
                    # we have a value for the attribute to be inverted
                    # get the condition for inverting
                    cond = valmap[attr]
                    if eval(cond):
                        # conditions are met
                        if isinstance(self.__dict__[attr], str):
                            # just change the sign on the string
                            oldval = self.__dict__[attr]
                            if oldval.startswith('-'):
                                self.__dict__[attr] = oldval[1:]        # remove the -
                            elif oldval.startswith('+'):
                                self.__dict__[attr] = '-' + oldval[1:]  # remove the +, add a -
                            else:
                                self.__dict__[attr] = '-' + oldval      # add a -
                        else:
                            # it's a number of some sort
                            self.__dict__[attr] = self.__dict__[attr] * -1


    def caluculate_field(self, rule):
        if len(rule) < 4:
            return # bad definition in the json file
        
        result = rule[0]
        field1 = rule[1]
        math = rule[2]
        field2 = rule[3]
        if getattr(self, result, None) is not None:
            # result field exists
            if getattr(self, field1, None) is not None \
                and getattr(self, field2, None) is not None:
                # we have all 3 the fields
                if math == 'plus':
                    self.__dict__[result] = self.__dict__[field1] + self.__dict__[field2]
                elif math == 'times':
                    self.__dict__[result] = self.__dict__[field1] * self.__dict__[field2]
            elif getattr(self, field1, None) is not None:
                # field2 is missing
                # just set the result to field1
                self.__dict__[result] = self.__dict__[field1]
            elif getattr(self, field2, None) is not None:
                # field1 is missing
                # just set the result to field2
                self.__dict__[result] = self.__dict__[field2]

        
    def get_formatted_string(self):
        result = ""
        for attr, id_char in zip(self.order, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n"

class SecurityRecord:
    def __init__(self, row=None, map=None):
        self.order = ['name', 'symbol', 'type', 'goal']
        self.ids =   ['N',    'S',      'T',    'G']

        self.typeTest = row[map.type] if row and map \
                        and getattr(map,"type",None) \
                        and len(row[map.type]) > 0 \
                        else None
        # translate security type to QIF terms?
        if self.typeTest is not None:
            self.valmap = getattr(map,"SecurityTypeMap",None)
            if self.valmap is not None:
                if self.typeTest in self.valmap:
                    self.typeTest = self.valmap[self.typeTest]

        # only fill out the record for 'Stock' or 'Option' types
        if self.typeTest is not None and (self.typeTest == 'Stock' or self.typeTest == 'Option'):
            self.type = self.typeTest
            self.symbol = row[map.symbol] if row and map \
                          and getattr(map,"symbol",None) is not None \
                          and len(row[map.symbol]) > 0 \
                          else None
            self.name = row[map.name] if row and map \
                        and getattr(map,"name",None) \
                        and self.symbol is not None \
                        and len(row[map.name]) > 0 \
                        else None
            self.goal = row[map.goal] if row and map \
                        and getattr(map,"goal",None) \
                        and self.symbol is not None \
                        and len(row[map.goal]) > 0 \
                        else None

    def get_formatted_string(self):
        result = ""
        for attr, id_char in zip(self.order, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n" if len(result) > 0 else None

#
#     @brief  Takes given CSV and parses it to be exported to a QIF
#
#     @params[in] inf_
#     File to be read and converted to QIF
#     @params[in] outf_
#     File that the converted data will go
#     @params[in] deff_
#     File with the settings for converting CSV
#
#
def readCsv(inf_,outf_,deff_): #will need to receive input csv and def file

    colmap = ColumnMap(deff_)
    if getattr(colmap, "CsvTimeFormat", None) is None:
        print("A CsvTimeFormat entry is required in the json definition file to parse the CSV date.")
        print("For example: 'CsvTimeFormat': '%m/%d/%y'")
        print("Formating is described here: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior")
        exit(1)

    if colmap.account and colmap.accountType is not None:
        acct_rec = StringIO()
        acct_rec.write("!Account\n")
        acct_rec.write("N" + colmap.account + "\n")
        acct_rec.write("T" + colmap.accountType + "\n")
        acct_rec.write("^\n")
        outf_.write(acct_rec.getvalue())
        acct_rec.close()

    csvIn = csv.reader(inf_, delimiter=colmap.Separator)  #create csv object using the given separator

    # if investment, make a pass thru to collect securities
    if colmap.accountType == "Invst":
        sec_rec = StringIO()
        sec_list = []
        for x in range(1, colmap.StartLine): #skip to start line
            next(csvIn,None)  #skip
        sec_len = 0
        for row in csvIn:
            rec = SecurityRecord(row, colmap)
            if getattr(rec, "type", None) is not None:
                if rec.symbol not in sec_list:
                    sec_list.append(rec.symbol)
                    if sec_len == 0:
                        sec_rec.write("!Type:Security\n")
                    sec_len += sec_rec.write(rec.get_formatted_string())
        if sec_len > 0:
            outf_.write(sec_rec.getvalue())
        sec_rec.close()
        inf_.seek(0)


    for x in range(1, colmap.StartLine): #skip to start line
        next(csvIn,None)  #skip

    transact_rec = StringIO()
    transact_len = 0
    for row in csvIn:
        rec = InvstRecord(row, colmap)
        if transact_len == 0:
            transact_rec.write("!Type:" + colmap.accountType + "\n")
        transact_len += transact_rec.write(rec.get_formatted_string())
    outf_.write(transact_rec.getvalue())
    transact_rec.close()

def is_float(text):
    # check for nan/infinity etc.
    if text.isalpha():
        return False
    try:
        locale.atof(text)
        return True
    except ValueError:
        return False

def convert():


    error = 'Input error!____ Format [import.csv] [output.csv] [import.def] ____\n\n\
                 [import.csv] = File to be converted\n\
                 [output.qif] = File to be created\n\
                 [import.def] = Definition file describing csv file\n'

    if (len(sys.argv) != 4):  #Check to make sure all the parameters are there
        print (error)
        exit(1)

    if os.path.isfile(sys.argv[1]):
         fromfile = open(sys.argv[1],'r')
    else:
        print ('\nInput error!____ import.csv: ' + sys.argv[1] + ' does not exist / cannot be opened !!\n')
        exit(1)

    try:
        tofile   = open(sys.argv[2],'w')
    except:
        print ('\nInput error!____ output.csv: ' + sys.argv[2] + ' cannot be created !!\n')
        exit(1)

    if os.path.isfile(sys.argv[3]):
        deffile = open(sys.argv[3],'r')
    else:
        print ('\nInput error!____ import.def: ' + sys.argv[3] + ' does not exist / cannot be opened !!\n')
        exit(1)
 
    # to handle commas and dots in numbers
    locale.setlocale(locale.LC_ALL, '')

    readCsv(fromfile,tofile,deffile)

    fromfile.close()
    tofile.close()
    deffile.close()



convert()#Start