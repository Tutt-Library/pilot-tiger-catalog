#-------------------------------------------------------------------------------
# Name:        solr_functions
# Purpose:
#
# Author:      Jeremy Nelson
#
# Created:     2014-01-30
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     MIT
#-------------------------------------------------------------------------------

def __get_fields_subfields__(marc_rec,
                             fields,
                             subfields):
    output = []
    for field in marc_rec.get('fields'):
        tag = field.keys()[0]
        if fields.count(tag) > 0:
            for row in field[tag]['subfields']:
                subfield = row.keys()[0]
                if subfields.count(subfield) > 0:
                    output.append(row[subfield])
    return output

def index_marc(solr_connection,
               marc):
    """Function takes a MARC JSON dict and indexes it into a Solr index.

    :param solr_connection: Solr.py Connection
    :param marc: JSON MARC record
    """
    solr_connection.add(id=str(marc.get("_id")),  # Usually MongoDB ID
                        author=__get_fields_subfields__(marc,
                                               ["100", "110", "111"],
                                               ["a"]),
                        topics=__get_fields_subfields__(marc,
                                               ['600', '610', '611', '630',
                                                '648', '650', '651', '653',
                                                '654', '655', '656', '657',
                                                '658', '662', '690', '691',
                                                '696', '697', '698', '699'],
                                                ['a', 'v', 'x', 'y', 'z']),
                        title=__get_fields_subfields__(marc,
                                              ["245"],
                                              ["a"]),
                        text=str(marc))


def main():
    pass

if __name__ == '__main__':
    main()
