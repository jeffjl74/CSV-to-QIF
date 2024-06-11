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
        if self.__dict__.get("Separator", None) is None:
            self.Separator = ","
        if self.__dict__.get("Type", None) is None:
            self.Type = "Bank"
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
        self.order = ['date', 'action', 'security', 'price', 'quantity', 'cleared', 'transfer_text', 'memo', 'commission', 'category', 'amount', 'amount_plus', 'amount_transferred']
        self.ids =   ['D',    'N',      'Y',        'I',     'Q',       'C',       'P',             'M',    'O',          'L',        'T',      'U',            '$']
        
        self.date_in = datetime.strptime(row[map.Date], map.CsvTimeFormat) if row and map and getattr(map,"Date",None) is not None else None
        self.date = datetime.strftime(self.date_in, map.QifTimeFormat) if self.date_in is not None else None
        
        self.action = row[map.Action] if row and map and getattr(map,"Action",None) is not None and len(row[map.Action]) > 0 else None
        # translate action to QIF terms?
        if self.action is not None:
            self.valmap = getattr(map,"ActionMap",None)
            if self.valmap is not None:
                if self.action in self.valmap:
                    self.action = self.valmap[self.action]

        self.security = row[map.Security] if row and map and getattr(map,"Security",None) is not None and len(row[map.Security]) > 0 else None
        self.price = row[map.Price] if row and map and getattr(map,"Price",None) is not None and len(row[map.Price]) > 0 else None
        self.multiplier = int(row[map.Multiplier]) if row and map and getattr(map,"Multiplier",None) is not None and len(row[map.Multiplier]) > 0 else 1
        self.quantity = int(row[map.Quantity]) * self.multiplier if row and map and getattr(map,"Quantity",None) is not None and len(row[map.Quantity]) > 0 and int(row[map.Quantity]) > 0 else None
        self.cleared = row[map.Cleard] if row and map and getattr(map,"Cleared",None) is not None and len(row[map.Cleared]) > 0 else None
        self.transfer_text = row[map.TransferText] if row and map and getattr(map,"TransferText",None) is not None and len(row[map.TransferText]) > 0 else None
        self.memo = row[map.Memo] if row and map and getattr(map,"Memo",None) is not None and len(row[map.Memo]) > 0 else None
        self.commission = row[map.Commission] if row and map and getattr(map,"Commission",None) is not None and len(row[map.Commision]) > 0 else None
        self.category = row[map.Category] if row and map and getattr(map,"Category",None) is not None and len(row[map.Category]) > 0 else None
        self.amount = row[map.TAmount] if row and map and getattr(map,"TAmount",None) is not None and len(row[map.TAmount]) > 0 else None
        self.amount_plus = row[map.UAmount] if row and map and getattr(map,"UAmount",None) is not None and len(row[map.UAmount]) > 0 else None
        self.amount_transferred = row[map.TransferAmount] if row and map and getattr(map,"TransferAmount",None) is not None and len(row[map.TransferAmount]) > 0 else None

        # invert anything?
        self.valmap = getattr(map, "InvertMap", None)
        if self.valmap is not None:
            for attr in self.valmap:
                if getattr(self, attr, None) is not None:
                    print(getattr(self[attr]))

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
        self.ids =   ['N',    'S',      'T',        'G']

        self.symbol = row[map.Security] if row and map and getattr(map,"Security",None) is not None and len(row[map.Security]) > 0 else None
        self.name = row[map.Name] if row and map and getattr(map,"Name",None) and self.symbol is not None and len(row[map.Name]) > 0 else self.symbol
        self.goal = row[map.Goal] if row and map and getattr(map,"Goal",None) and self.symbol is not None and len(row[map.Goal]) > 0 else None
        self.type = row[map.Instrument] if row and map and getattr(map,"Instrument",None) and self.symbol is not None and len(row[map.Instrument]) > 0 else None
        # translate security type to QIF terms?
        if self.type is not None:
            self.valmap = getattr(map,"SecurityTypeMap",None)
            if self.valmap is not None:
                if self.type in self.valmap:
                    self.type = self.valmap[self.type]

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

    if colmap.Account and colmap.Type is not None:
        acct_rec = StringIO()
        acct_rec.write("!Account\n")
        acct_rec.write("N" + colmap.Account + "\n")
        acct_rec.write("T" + colmap.Type + "\n")
        acct_rec.write("^\n")
        outf_.write(acct_rec.getvalue())
        acct_rec.close()

    csvIn = csv.reader(inf_, delimiter=colmap.Separator)  #create csv object using the given separator

    # if investment, make a pass thru to collect securities
    if colmap.Type == "Invst":
        sec_rec = StringIO()
        sec_list = []
        for x in range(1, colmap.StartLine): #skip to start line
            next(csvIn,None)  #skip
        sec_len = 0;
        for row in csvIn:
            rec = SecurityRecord(row, colmap)
            if rec.symbol is not None:
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
            transact_rec.write("!Type:" + colmap.Type + "\n")
        transact_len += transact_rec.write(rec.get_formatted_string())
    outf_.write(transact_rec.getvalue())
    transact_rec.close()

def write_file(rec, acct_type, file_):
    # outFile = open(file_,"a")  #Open file to be appended

    file_.write("!Type:" + acct_type + "\n")

    file_.write(rec)
    #outFile.write("\n")
    # file_.close()



#
#     @brief Receives data to be written to and its location
#
#     @params[in] date_
#     Data of transaction
#     @params[in] amount_
#     Amount of money for transaction
#     @params[in] memo_
#     Description of transaction
#     @params[in] payee_
#     Transaction paid to
#     @params[in] filelocation_
#     Location of the Output file
#
#
# https://en.wikipedia.org/wiki/Quicken_Interchange_Format
#
def writeFile(type_,date_,amount_,memo_,payee_, filelocation_):
    outFile = open(filelocation_,"a")  #Open file to be appended
    outFile.write("!Type:" + type_ + "\n")
    outFile.write("D")  #Date line starts with the capital D
    outFile.write(date_)
    outFile.write("\n")

    outFile.write("T")  #Transaction amount starts here
    outFile.write(amount_)
    outFile.write("\n")

    outFile.write("M")  #Memo Line
    outFile.write(memo_)
    outFile.write("\n")

    if(payee_!=-1):
        outFile.write("P")  #Payee line
        outFile.write(payee_)
        outFile.write("\n")

    outFile.write("^\n")  #The last line of each transaction starts with a Caret to mark the end
    outFile.close()
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

    #  tofile = sys.argv[2]
     readCsv(fromfile,tofile,deffile)

     fromfile.close()
     tofile.close()
     deffile.close()



convert()#Start