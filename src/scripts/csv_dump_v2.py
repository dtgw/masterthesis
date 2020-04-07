 #!/usr/bin/env python3 

import psycopg2
import argparse
import textwrap
import sys
from datetime import datetime

import pandas as pd

db = psycopg2.connect(
    database="thesis",
    user='thesis',
    password='carpestudentem',
    host="revuedesingenieurs.be",
    port="5432"
)

cursor = db.cursor()

def query_feature_values(mode, selection=None):
    """ Query feature values to remote database"""
    cond = ""
    multiplicator = 119

     # if boolean features only
    if mode == 1:
        multiplicator = 0
        for f_id in get_boolean_id():
            multiplicator += 1
            cond += " {},".format(f_id[0])
        
        #build the condition, [:-1] is there to pick up the last ","
        cond = "AND F.num IN (" + cond[:-1] + ") "
    elif mode == 2:
        multiplicator = len(selection)
        for f in selection:
            cond += " {},".format(f)

        #build the condition, [:-1] is there to pick up the last ","
        cond = "AND F.num IN (" + cond[:-1] + ") "

    print("Request feature values")
    cursor.execute("""
        SELECT FV.malware_id, F.num, FV.value, M.date
        FROM features F, feature_values FV, malwares M
        WHERE FV.feature_id = F.id 
        AND FV.malware_id = M.id
        {}
        ORDER BY FV.malware_id, F.num;
    """.format(cond))
    features = cursor.fetchall()
    return features

def get_boolean_id():
    """ Returns the num of the boolean values"""
    print("Request boolean values")
    cursor.execute("""
        SELECT DISTINCT F.num 
        FROM features F, feature_values FV 
        WHERE FV.feature_id NOT IN 
            (SELECT DISTINCT A.feature_id 
             FROM feature_values A
             WHERE A.value != 0
                AND A.value != 1)
            AND FV.feature_id = F.id
        ORDER BY F.num;
    """)
    boolean_id = cursor.fetchall()
    print("The num of boolean values are : {}".format(boolean_id))
    return boolean_id

def get_feature_labels(array):
    """ Returns the different features for the first malware"""
    print("feature_labels \n")
    first_malware = array[0][0]
    feature_labels = []
    for row in array:
        malware_id = row[0]
        feature_number = row[1]
        if malware_id != first_malware:
            return feature_labels
        feature_labels.append(feature_number)

def get_feature_values(array, number_of_features):
    """Returns a 2D array with the following structure :
       [[date, malware_1, feature_1, feature_2, feature3, ...],
        ...
        [date, malware_14, feature1, feature_2, feature_3, ...]]"""
    current_id = -1
    tmp_features = []
    malwares_error = []
    final_array = []

    for row in array:
        malware_id = row[0]
        date = row[3]
        feature_value = row[2]

        if current_id != malware_id:

            if len(tmp_features) == number_of_features + 2: 
                final_array.append(tmp_features)
            else:
                malwares_error.append(malware_id)

            tmp_features = []
            tmp_features.append(date)
            tmp_features.append(malware_id)
            current_id = malware_id

        tmp_features.append(feature_value)

    print("There is some trouble with {} malware(s) " \
        .format(len(malwares_error)))

    return final_array

def gen_labels_info():
    cursor.execute("""
        SELECT DISTINCT D.malware_id as malware_id,
               E.error,
               N.none,
               O.other,
               M.packer,
               M.max
        FROM detections D
        FULL JOIN  (
            SELECT malware_id, count(*) as error
            FROM detections
            WHERE packer like 'error' AND clean
            GROUP BY malware_id) E
        ON D.malware_id = E.malware_id
        FULL JOIN  (
            SELECT malware_id, count(*) as none
            FROM detections
            WHERE packer like 'none' AND clean
            GROUP BY malware_id) N
        ON D.malware_id = N.malware_id
        FULL JOIN  (
            SELECT malware_id, count(*) as other
            FROM detections
            WHERE packer NOT like 'error' AND packer NOT like 'none' AND clean
            GROUP BY malware_id) O
        ON D.malware_id = O.malware_id
        FULL JOIN  (
            SELECT malware_id, packer ,count(*) as max
            FROM detections
            WHERE packer NOT like 'error' AND packer NOT like 'none' AND clean
            GROUP BY malware_id, packer) M
            ON D.malware_id = M.malware_id
        ORDER BY malware_id;
    """)
    return cursor.fetchall()

def zero_if_null(value):
    return value if value else 0 

def cleaned_labels(labels):
    for (m_id, error, none, other, packer, number) in labels:
        error = zero_if_null(error)
        none = zero_if_null(none)
        other = zero_if_null(other)
        number = zero_if_null(number)
        if error + none + other == 5:
            yield (m_id, error, none, other, packer, number)

def get_labels(threshold):
    assert threshold >= 3
    buff = []
    data = gen_labels_info()
    for (m_id, error, none, other, packer, number) in cleaned_labels(data):
        if none >= threshold:
            buff.append((m_id, 0))
        elif other >= threshold:
            buff.append((m_id, 1))
    return buff

def merge_fv_and_label(feature_values, labels):
    """Merge feature values with corresponding label"""
    fv_index = 0
    label_index = 0 
    global_array = []

    while(fv_index < len(feature_values) and label_index < len(labels)):
        # Corresponding malware id
        if feature_values[fv_index][1] == labels[label_index][0]:
            new_row = [feature_values[fv_index][0]] + feature_values[fv_index][2:] + [labels[label_index][1]]
            global_array.append(new_row)
            fv_index += 1
            label_index += 1
        elif feature_values[fv_index][1] < labels[label_index][0]:
            fv_index += 1
        else:
            label_index += 1

    '''print("{:.2%} of feature values in the final" \
        .format(len(global_array)/len(feature_values)))
    print("{:.2%} of labels in the final" \
        .format(len(global_array)/len(labels)))'''

    return global_array

def create_csv(array, labels, start, limit):
    now = datetime.now()
    timestamp = now.strftime("%Y.%m.%d-%H.%M")
    df = pd.DataFrame(data=array,
                      index=[ i for i in range(len(array)) ],
                      columns=['date'] + [ 'f'+str(i) for i in labels ] + ['label'])
    df.sort_values(by='date', ascending=1, inplace=True)
    indexNames = df[df['date'] < start].index
    df.drop(indexNames, inplace=True)
    df.drop('date', 1, inplace=True)
    if limit == None or limit > df.shape[0]:
        limit = df.shape[0]
    df = df[:limit]
    df.to_csv('../dumps/'+timestamp+'.csv', index=False)
    print("File {}.csv created".format(timestamp))

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-t",
                        "--threshold",
                        type=int,
                        help="Threshold for ground truth generation (max. 5)",
                        default=3)
    parser.add_argument("-l",
                        "--limit", 
                        type=int, 
                        help="Limit number of malwares")
    parser.add_argument("-m",
                        "--mode",
                        type=int,
                        help=textwrap.dedent('''\
                                0 (default): all features
                                1: only boolean features
                                2: features from parameter array
                                 '''),
                        default=0)
    parser.add_argument("-a",
                        "--arr",
                        nargs="+", 
                        help="Array of wanted features e.g. 46 87 101 119")
    parser.add_argument("-d",
                        "--detector",
                        nargs="+",
                        help=textwrap.dedent('''\
                            Array of wanted detectors with values 
                            in [peframe, peid, manalyze, cisco, detect-it-easy]
                            '''))
    parser.add_argument("-e",
                        "--error",
                        type=bool,
                        help="Consider detection errors as a packed label",
                        default=False)
    parser.add_argument("-s",
                        "--start", 
                        help=textwrap.dedent('''\
                            Month from which malwares should be picked up according
                            to the following format : 20191231
                            '''),
                        default="20190615")

    args = parser.parse_args()
    if args.mode == 2 and args.arr is None:
        parser.error("mode 2 requires array of features, -h for help")
    result_of_db = query_feature_values(args.mode, args.arr)
    name_of_features = get_feature_labels(result_of_db)
    print("Number of features: {}".format(len(name_of_features)))
    features = get_feature_values(result_of_db, len(name_of_features))
    labels = get_labels(args.threshold)
    final_array = merge_fv_and_label(features, labels)
    create_csv(final_array, name_of_features, args.start, args.limit)

if __name__ == '__main__':
    main()

