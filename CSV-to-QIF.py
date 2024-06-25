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
import csv
import json
import argparse

class ColumnMap:
    def __init__(self, deff_):
        """
        Reads all of the name/value entries in the passed JSON file
        into a self dictionary. If the value of a Name/value pair
        is a single letter, it is converted to an integer offset
        from the letter 'A' (or 'a').

        Args:
            deff_ (file): The JSON file opened for reading.
        """
        try:
            csvdeff = json.load(deff_)
        except json.JSONDecodeError as e:
            print("Invalid JSON syntax:", e)
            exit(1)

        upperffset = ord("A")
        loweroffset =  ord("a")

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
            self.QifTimeFormat = "%d/%m/%Y"
        if self.__dict__.get("CurrencySymbol", None) is None:
            self.CurrencySymbol = ""

class AccountRecord:
    def __init__(self, map):
        """
        Parses the passed JSON ColumnMap into class variables which
        can be used to construct a QIF !Account record.

        Args:
            map (ColumnMap): Contains the JSON to CSV data mapping.
        """
        self.fields = ['account', 'accountType', 'taxRate', 'description', 'limit', 'balance']
        self.ids =    ['N',       'T',           'R',       'D',           'L',     '$']

        self.account = getattr(map,"account",None)
        self.accountType = getattr(map,"accountType", None)
        self.taxRate = locale.atof(getattr(map,"taxRate")) if map \
                        and getattr(map,"taxRate",None) is not None \
                        else None
        self.description = getattr(map,"description",None)
        self.limit = getattr(map,"limit",None)
        self.balance = None # placeholder for balance collected from the csv

    def get_formatted_string(self):
        if getattr(self, "account", None) is not None:
            result = "!Account\n"
        else:
            result = ""
        for attr, id_char in zip(self.fields, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n"

class BankRecord:
    def __init__(self, row, map):
        """
        Parses the passed CSV row and JSON ColumnMap into class variables which
        can be used to construct a QIF !Type:Bank record.

        Args:
            row (csv.reader row): Incomming CSV data.
            map (ColumnMap): Contains the JSON to CSV data mapping.
        """
        self.fields = ['date', 'amountT', 'amountU', 'cleared', 'checkNum', 'payee', 'memo', 'address', 'category', 'categoryInSplit', 'memoInSplit', 'amountOfSplit', 'percentageOfSplit', "reimbursable"]
        self.ids =    ['D',    'T',       'U',       'C',       'N',        'P',     'M',    'A',       'L',        'S',               'E',           '$',              '%',                'F']

        self.date_in = datetime.strptime(row[map.date], map.CsvTimeFormat) \
                        if row and map \
                        and getattr(map,"date",None) is not None \
                        else None
        self.date = datetime.strftime(self.date_in, map.QifTimeFormat) \
                        if self.date_in is not None \
                        else None
        self.amountT = locale.atof(row[map.amountT].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"amountT",None) is not None \
                        and len(row[map.amountT]) > 0 \
                        else None
        self.amountU = locale.atof(row[map.amountU].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"amountU",None) is not None \
                        and len(row[map.amountU]) > 0 \
                        else None
        # keeping only the first letter of the "cleared" column, may not work for all files
        # (i.e. works if the column says "Cleared", "Reconciled", or blank/missing)
        self.cleared = row[map.cleared][:1] if row and map \
                        and getattr(map,"cleared",None) is not None \
                        and len(row[map.cleared]) > 0 \
                        else None
        self.checkNum = row[map.checkNum] if row and map \
                        and getattr(map,"checkNum",None) is not None \
                        and len(row[map.checkNum]) > 0 \
                        else None
        self.payee = row[map.payee] if row and map \
                        and getattr(map,"payee",None) is not None \
                        and len(row[map.payee]) > 0 \
                        else None
        self.memo = row[map.memo] if row and map \
                        and getattr(map,"memo",None) is not None \
                        and len(row[map.memo]) > 0 \
                        else None
        self.address = row[map.address] if row and map \
                        and getattr(map,"address",None) is not None \
                        and len(row[map.address]) > 0 \
                        else None
        self.category = row[map.category] if row and map \
                        and getattr(map,"category",None) is not None \
                        and len(row[map.category]) > 0 \
                        else None
        self.categoryInSplit = row[map.categoryInSplit] if row and map \
                        and getattr(map,"categoryInSplit",None) is not None \
                        and len(row[map.categoryInSplit]) > 0 \
                        else None
        self.memoInSplit = row[map.memoInSplit] if row and map \
                        and getattr(map,"memoInSplit",None) is not None \
                        and len(row[map.memoInSplit]) > 0 \
                        else None
        self.amountOfSplit = locale.atof(row[map.amountOfSplit].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"amountOfSplit",None) is not None \
                        and len(row[map.amountOfSplit]) > 0 \
                        else None
        self.percentageOfSplit = locale.atof(row[map.percentageOfSplit].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"percentageOfSplit",None) is not None \
                        and len(row[map.percentageOfSplit]) > 0 \
                        else None
        self.reimbursable = row[map.reimbursable] if row and map \
                        and getattr(map,"reimbursable",None) is not None \
                        and len(row[map.reimbursable]) > 0 \
                        else None

        # we can also collect the balance to support the AccountRecord
        self.balance = locale.atof(row[map.balance].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"balance",None) is not None \
                        and len(row[map.balance]) > 0 \
                        else None
        # and create a couple of non-QIF intermediate fields for credit card calculation
        self.Credit = locale.atof(row[map.Credit].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"Credit",None) is not None \
                        and len(row[map.Credit]) > 0 \
                        else None
        self.Debit = locale.atof(row[map.Debit].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"Debit",None) is not None \
                        and len(row[map.Debit]) > 0 \
                        else None


        # any caluculated fields?
        valmap = getattr(map, "CalculationRules", None)
        if valmap is not None:
            for attr in valmap:
                # we have a calculation
                expr = valmap[attr]
                caluculate_field(self, attr, expr)

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
                        invert_field(self, attr)

    def get_formatted_string(self):
        """
        Constructs a QIF !Type:Bank record from the class variables.

        Returns:
            string: The !Type:Bank record (not including the !Type:Bank line).
        """
        result = ""
        for attr, id_char in zip(self.fields, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n"

class InvstRecord:
    def __init__(self, row, map):
        """
        Parses the passed CSV row and JSON ColumnMap into class variables which
        can be used to construct a QIF !Type:Invst record.

        Args:
            row (csv.reader row): Incomming CSV data.
            map (ColumnMap): Contains the JSON to CSV data mapping.
        """
        self.fields = ['date', 'action', 'security', 'price', 'quantity', 'cleared', 'transfer_text', 'memo', 'commission', 'category', 'amountT', 'amountU', 'amount_transferred']
        self.ids =    ['D',    'N',      'Y',        'I',     'Q',        'C',       'P',             'M',    'O',          'L',        'T',       'U',       '$']

        self.date_in = datetime.strptime(row[map.date], map.CsvTimeFormat) \
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
        self.action = row[map.action] if row and map \
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

        self.price = abs(locale.atof(row[map.price].strip(map.CurrencySymbol))) if row and map \
                        and getattr(map,"price",None) is not None \
                        and len(row[map.price]) > 0 \
                        else None
        self.quantity = locale.atof(row[map.quantity].strip(map.CurrencySymbol)) \
                        if row and map and getattr(map,"quantity",None) is not None \
                        and len(row[map.quantity]) > 0 \
                        and int(row[map.quantity]) > 0 \
                        else None
        self.cleared = row[map.cleard] if row and map \
                        and getattr(map,"cleared",None) is not None \
                        and len(row[map.cleared]) > 0 \
                        else None
        self.transfer_text = row[map.transfer_text] if row and map \
                        and getattr(map,"transfer_text",None) is not None \
                        and len(row[map.transfer_text]) > 0 \
                        else None
        self.commission = locale.atof(row[map.commission].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"commission",None) is not None \
                        and len(row[map.commission]) > 0 \
                        and is_float(row[map.commission]) \
                        else None
        self.category = row[map.category] if row and map and \
                        getattr(map,"category",None) is not None \
                        and len(row[map.category]) > 0 \
                        else None
        self.amountT = locale.atof(row[map.amountT].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"amountT",None) is not None \
                        and len(row[map.amountT]) > 0 \
                        else None
        self.amountU = locale.atof(row[map.amountU].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"amountU",None) is not None \
                        and len(row[map.amountU]) > 0 \
                        else None
        self.amount_transferred = locale.atof(row[map.amount_transferred]) if row and map \
                        and getattr(map,"amount_transferred",None) is not None \
                        and len(row[map.amount_transferred]) > 0 \
                        else None

        # extra columns that are not part of a QIF record but we want to capture
        self.Fees = locale.atof(row[map.Fees].strip(map.CurrencySymbol)) if row and map \
                        and getattr(map,"Fees",None) is not None \
                        and len(row[map.Fees]) > 0 \
                        else None
        self.Multiplier = int(row[map.Multiplier]) if row and map \
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
                    caluculate_field(self, attr, expr)

        # any translations?
        valmap = getattr(map, "Translations", None)
        if valmap is not None:
            # we have translation rules
            for attr in valmap:
                # do we have the field it wants to translate?
                if attr in self.fields:
                    entries = len(valmap[attr])
                    if entries % 2 == 0:
                        for x in range(0, entries, 2):
                            cond = valmap[attr][x]
                            newval = valmap[attr][x+1]
                            if eval(cond):
                                # condition is true
                                self.__dict__[attr] = newval

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
                        invert_field(self, attr)
        
    def get_formatted_string(self):
        """
        Constructs a QIF !Type:Invst record from the class variables.

        Returns:
            string: The !Type:Invst record (not including the !Type:Invst line).
        """
        result = ""
        for attr, id_char in zip(self.fields, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n"

class SecurityRecord:
    def __init__(self, row, map):
        """
        Parses the passed CSV row and JSON ColumnMap into class variables which
        can be used to construct a QIF !Type:Security record.

        Args:
            row (csv.reader row): Incomming CSV data.
            map (ColumnMap): Contains the JSON to CSV data mapping.
        """
        self.fields = ['security', 'symbol', 'type', 'goal']
        self.ids =    ['N',        'S',      'T',    'G']

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
            self.security = row[map.security] if row and map \
                        and getattr(map,"security",None) \
                        and self.symbol is not None \
                        and len(row[map.security]) > 0 \
                        else None
            self.goal = row[map.goal] if row and map \
                        and getattr(map,"goal",None) \
                        and self.symbol is not None \
                        and len(row[map.goal]) > 0 \
                        else None

            # any translations?
            valmap = getattr(map, "Translations", None)
            if valmap is not None:
                # we have translation rules
                for attr in valmap:
                    # do we have the field it wants to translate?
                    if attr in self.fields:
                        entries = len(valmap[attr])
                        if entries % 2 == 0:
                            for x in range(0, entries, 2):
                                cond = valmap[attr][x]
                                newval = valmap[attr][x+1]
                                if eval(cond):
                                    # condition is true
                                    self.__dict__[attr] = newval

    def get_formatted_string(self):
        """
        Constructs a QIF !Type:Security record from the class variables.

        Returns:
            string: The !Type:Security record (not including the !Type:Security line).
        """
        result = ""
        for attr, id_char in zip(self.fields, self.ids):
            value = getattr(self, attr)
            if value is not None:
                result += f"{id_char}{value}\n"
        return result + "^\n" if len(result) > 0 else None

def readCsv(inf_, outf_, colmap):
    """
    Reads the CSV file and writes the QIF file using a column map.

    Args:
        inf_ (file):  The CSV input file opened for reading.
        outf_ (file): The QIF file opened for writing.
        colmap (ColumnMap) : The results of parsing the JSON defnition file.

    Returns:
        None
    """

    csvIn = csv.reader(inf_, delimiter=colmap.Separator)  #create csv object using the given separator

    # fill out the account record if the json spec has an account name
    if colmap.account and colmap.accountType is not None:
        acct_rec = AccountRecord(colmap)
        if acct_rec.accountType != 'Invst' \
            and getattr(colmap, "balance", None) is not None:
            # we have a bank balance column
            # make a pass through the csv and collect the balance with the latest date
            for x in range(1, colmap.StartLine): #skip to start line
                next(csvIn,None)  #skip
            latestDate = datetime.min # little date, everything will be newer than this
            try:
                for row in csvIn:
                    rec = BankRecord(row, colmap)
                    if getattr(rec, "date", None) is not None \
                        and getattr(rec, "balance", None) is not None:
                        # update the balance?
                        rec_time = datetime.strptime(rec.date, colmap.QifTimeFormat)
                        if rec_time > latestDate:
                            acct_rec.balance = rec.balance
                            latestDate = rec_time
            except:
                print("CSV file error (AccountRecord). CSV file may not conform to the json definition file.")
            inf_.seek(0)
        outf_.write(acct_rec.get_formatted_string())

    # if investment, make a pass thru to collect securities
    if colmap.accountType == "Invst":
        sec_rec = StringIO()
        sec_list = [] # only need each security once, track what we've seen
        for x in range(1, colmap.StartLine): #skip to start line
            next(csvIn,None)  #skip
        sec_len = 0
        try:
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
        except:
            print("CSV file error (SecurityRecord). CSV file may not conform to the json definition file.")
        inf_.seek(0)


    for x in range(1, colmap.StartLine): #skip to start line
        next(csvIn,None)  #skip

    transact_rec = StringIO()
    transact_len = 0
    try:
        for row in csvIn:
            if colmap.accountType == "Invst":
                rec = InvstRecord(row, colmap)
            else:
                rec = BankRecord(row, colmap)
            if transact_len == 0:
                transact_rec.write("!Type:" + colmap.accountType + "\n")
            transact_len += transact_rec.write(rec.get_formatted_string())
        outf_.write(transact_rec.getvalue())
        transact_rec.close()
    except:
        print("CSV file error (data record). CSV file may not conform to the json definition file.")
    
def invert_field(recordClass, attr):
    """
    Change the sign of the class variable 'attr' in the class 'recordClass'.

    Args:
        self (class): Class containing the variable 'attr'.
        attr (string): Name of the class variable to invert.
    """
    if isinstance(recordClass.__dict__[attr], str):
        # just change the sign on the string
        oldval = recordClass.__dict__[attr]
        if oldval.startswith('-'):
            recordClass.__dict__[attr] = oldval[1:]        # remove the -
        elif oldval.startswith('+'):
            recordClass.__dict__[attr] = '-' + oldval[1:]  # remove the +, add a -
        else:
            recordClass.__dict__[attr] = '-' + oldval      # add a -
    else:
        # it's a number of some sort
        recordClass.__dict__[attr] = recordClass.__dict__[attr] * -1

def caluculate_field(recordClass, attr, rule):
    """
    Perform the math defined by the 'rule' to update the
    'recordClass' varialbe 'attr'. Variables named in the
    'rule' must not be strings (currently can't do math on strings).

    Args:
        recordClass (class): The class containing the variables
                             defined in the rule and attr.
        attr (string): The name of the class variable to update.
        rule (string array): Defines the math to perform:
            array[0]: Class variable name
            array[1]: Operation to perform, either "+", "-", "/", or "*"
            array[2]: Class variable name
    """
    if len(rule) < 3:
        return # bad definition in the json file
    
    field1 = rule[0]
    math = rule[1]
    field2 = rule[2]
    if getattr(recordClass, field1, None) is not None \
        and getattr(recordClass, field2, None) is not None:
        # we have all 3 the fields
        string1 = isinstance(recordClass.__dict__[field1], str)
        string2 = isinstance(recordClass.__dict__[field2], str)
        if string1 or string2:
            # can't do math on strings
            print("error: CalculateRules ", attr, "=", rule, " must be non-string inputs")
            return
        if math == '+':
            recordClass.__dict__[attr] = recordClass.__dict__[field1] + recordClass.__dict__[field2]
        elif math == '-':
            recordClass.__dict__[attr] = recordClass.__dict__[field1] - recordClass.__dict__[field2]
        elif math == '*':
            recordClass.__dict__[attr] = recordClass.__dict__[field1] * recordClass.__dict__[field2]
        elif math == '/':
            if field2 == 0:
                print("Cannot divide by zero:", attr, rule, recordClass.get_formatted_string())
            else:
                recordClass.__dict__[attr] = recordClass.__dict__[field1] / recordClass.__dict__[field2]
    elif getattr(recordClass, field1, None) is not None:
        # field2 is missing
        # just set the result to field1
        recordClass.__dict__[attr] = recordClass.__dict__[field1]
    elif getattr(recordClass, field2, None) is not None:
        # field1 is missing
        # just set the result to field2
        recordClass.__dict__[attr] = recordClass.__dict__[field2]

def translate_field(recordClass, attr, rule):
    if len(rule) < 2:
        return # bad definition in the json file
    cond = rule[0]
    newval = rule[1]
    if eval(cond):
        # condition is true
        recordClass.__dict__[attr] = newval

def is_float(text):
    """
    Tests whether the passed 'text' can be converted to float.

    Args:
        text (string): Text to test.

    Returns:
        True if 'text' can convert to a float.
        False if 'text' does not convert to a float.
    """
    # check for nan/infinity etc.
    if text.isalpha():
        return False
    try:
        locale.atof(text.strip(map.CurrencySymbol))
        return True
    except ValueError:
        return False

def convert():
    """
    Parses command line and JSON definiton file, verifies inputs,
    and calls readCsv() if all is well.
    """
    # set locale so we handle commas and dots in numbers
    locale.setlocale(locale.LC_ALL, '')

    parser = argparse.ArgumentParser(description='Convert CSV file to QIF',
            epilog='More info here: https://github.com/jeffjl74/CSV-to-QIF')
    parser.add_argument('-i', dest ='csvFile', 
                    action ='store', help ='CSV file to convert')
    parser.add_argument('-o', dest ='qifFile', 
                    action ='store', help ='QIF file to create')
    parser.add_argument(dest='jsonFile',
                    action ='store', help ='JSON conversion definition file')
    args = parser.parse_args()

    params_ok = True
    colmap = None
    fromPath = ''
    toPath = ''
    if args.jsonFile is not None:
        # process the json file
        defPath = args.jsonFile
        if not os.path.isfile(defPath):
            print("error: Could not find json file ", defPath)
            params_ok = False
        else:
            defFile = open(defPath,'r')
            colmap = ColumnMap(defFile)
            defFile.close()
            # get file paths from the json
            # but they could be overridden by the command line parameter
            fromFileName = getattr(colmap, "CsvFile", "")
            fromFolder = getattr(colmap, "CsvFolder", "")
            toFileName = getattr(colmap, "QifFile", "")
            toFolder = getattr(colmap, "QifFolder", "")
            # get/build CSV file name
            if args.csvFile and os.path.dirname(args.csvFile):
                # parameter is the full spec
                fromPath = args.csvFile
            elif fromFolder and args.csvFile and not os.path.dirname(args.csvFile):
                # json has a folder, parameter does not
                # combine json & parameter
                fromPath = os.path.join(fromFolder, args.csvFile)
            elif not args.csvFile:
                # there is no cmd line parameter
                # (json might be empty, which is checked later)
                fromPath = os.path.join(fromFolder, fromFileName)
            else:
                # there is no json spec
                # use the parameter
                # (param might be empty, which is checked later)
                fromPath = args.csvFile

            # get/build QIF file name
            if args.qifFile and os.path.dirname(args.qifFile):
                # parameter is the full spec
                toPath = args.qifFile
            elif toFolder and args.qifFile and not os.path.dirname(args.qifFile):
                # json has a folder, parameter does not
                # combine json & parameter
                toPath = os.path.join(toFolder, args.qifFile)
            elif not args.qifFile:
                # there is no cmd line parameter
                # (json might be empty, which is checked later)
                toPath = os.path.join(toFolder, toFileName)
            else:
                # there is no json spec
                # use the parameter
                # (param might be empty, which is checked later)
                toPath = args.qifFile

    # verify we have file names
    if not fromPath:
        print("error: A CSV file name is required, either on the command line or in the json file.")
        params_ok = False
    if not toPath:        
        print("error: A QIF file name is required, either on the command line or in the json file.")
        params_ok = False

    # ck existance, print problem(s)
    if not os.path.isfile(fromPath):
        print("error: Cound not find input CSV file:", fromPath)
        params_ok = False
    if not os.path.exists(os.path.dirname(os.path.abspath(toPath))):
        print("error: QIF directory does not exist:", toFolder)
        params_ok = False
    if not os.path.isfile(defPath):
        print("error: Could not find json file ", defPath)
        params_ok = False

    if not params_ok:
        exit(1)
    
    try:
        fromfile = open(fromPath,'r')
    except:
        print ('\n** Exception reading ' + fromPath)
        exit(1)

    try:
        tofile = open(toPath,'w')
    except:
        print ('\n** Exception writing ' + toPath)
        exit(1)

    if getattr(colmap, "CsvTimeFormat", None) is None:
        print("A CsvTimeFormat entry is required in the json definition file to parse the CSV date.")
        print("For example: 'CsvTimeFormat': '%m/%d/%y'")
        print("Formating is described here: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior")
        exit(1)

    readCsv(fromfile, tofile, colmap)

    fromfile.close()
    tofile.close()



convert()#Start