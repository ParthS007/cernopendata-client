from __future__ import print_function

import argparse
import os
import sys

import requests

BASE_RECORD_URL = "http://opendata.cern.ch/record/"
BASE_API_URL = "http://opendata.cern.ch/api/records/"


def verify_recid(recid):
    """Verify that recid corresponds to a valid Open Data record webpage."""
    if recid is None:
        sys.exit(
            "ERROR: You must supply a record id number as an " "input using -r flag."
        )
    else:
        input_record_url = BASE_RECORD_URL + str(recid)
        input_record_url_check = requests.get(input_record_url)

        if input_record_url_check.status_code == requests.codes.ok:
            base_record_ID = str(recid)
            return base_record_ID
        else:
            try:
                input_record_url_check.raise_for_status()
            except requests.HTTPError as http_error_msg:
                print("ERROR: The record id number you supplied is not valid.")
                sys.exit(http_error_msg)
            return False


def get_recid_api(base_record_id):
    """Get the api for the record with given recid. """
    record_api_url = BASE_API_URL + base_record_id
    record_api = requests.get(record_api_url)
    record_api.raise_for_status()
    return record_api


def get_datasets(record_api):
    """Get the list of datasets that are linked on this page to be used for
    this example. Each element of this list is a single item dictionary
    with the key 'recid' paired with the record number of the dataset
    as the value.
    """
    try:
        dataset_links = record_api.json()["metadata"]["use_with"]["links"]
        print(
            "Getting index files for '"
            + record_api.json()["metadata"]["title"]
            + "'...\n"
        )
        return dataset_links
    except KeyError:
        sys.exit(
            "ERROR: This Open Data record does not contain "
            "a list of links to dataset index files."
        )


def dataset_convert_to_ids(dataset_links):
    """Convert this list of single item dictionaries into a list that just
    contains the record number for each dataset. If the same dataset id appears
    twice within datset_links, the duplicates are skipped and the dataset id
    is only included once.
    """
    dataset_ids = []
    for dataset_dict in dataset_links:
        rec_id = dataset_dict["recid"]
        if rec_id in dataset_ids:
            print(
                "Warning: The dataset for record "
                + rec_id
                + " is listed more than once. Skipping duplicate..."
            )
        else:
            dataset_ids.append(rec_id)

    return dataset_ids


def check_file_size(file_size, file_path):
    """As a sanity check, we make sure that the file size of
    the downloaded index file matches the size listed in the json info."""
    if file_size != os.path.getsize(file_path):
        print(
            "Warning: The file size for the download {} does not match"
            " the size listed on the Open Data API.".format(file_path)
        )


def get_record_from_url(record_num):
    record_url = BASE_RECORD_URL + record_num + "/export/json"
    record = requests.get(record_url)
    record.raise_for_status()
    return record


def get_index_files(record, database_title, record_num):
    try:
        index_files = record.json()["metadata"]["index_files"]
        return index_files
    except KeyError:
        print(
            "Warning: The database link to "
            + database_title
            + " (record: "
            + record_num
            + ") does not contain any index files."
        )


def get_database_title(record):
    database_title = record.json()["metadata"]["title"]
    database_title = "/".join(database_title.split("/")[1:-1])
    return database_title


def foo(base_record_id, dataset_ids):
    # **********************************************************************
    # For each dataset id number, get the opendata record page json file.  *
    #    Get the list of index files that are listed on this record page.  *
    #    Each item in this list is a dicitonary containing information on  *
    #    the index file. It is important to note that each index file is   *
    #    listed twice, once as a json file and once as as a txt file. We   *
    #    are only interested in downloading the txt files.                 *
    #                                                                      *
    #    For each index file, use the url listed in its dicitonary to get  *
    #    the txt file and write/save a copy of it.                         *

    # **********************************************************************
    total_file_count = 0
    output_folder_path = "rec" + base_record_id + "_datasets/"

    for record_num in dataset_ids:

        database_file_count = 0

        record = get_record_from_url(record_num)
        database_title = get_database_title(record)
        index_files = get_index_files(record, database_title, record_num)

        for index_file in index_files:
            filename = index_file["filename"]

            if ".txt" in filename:
                txt_file = requests.get(index_file["uri_http"])
                file_size = index_file["size"]
                filepath = output_folder_path + database_title + "/" + filename
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "wb") as fi:
                    fi.write(txt_file.content)
                    database_file_count += 1

                check_file_size(file_size, filepath)

        print(
            "Downloaded "
            + str(database_file_count)
            + " index files from "
            + database_title
        )
        total_file_count += database_file_count

    print(
        "\nQuery Complete: Downloaded "
        + str(total_file_count)
        + " index files to the folder ./"
        + output_folder_path
    )


def main():
    # **********************************************************************
    # Configure command line arguments                                     *
    # **********************************************************************

    # TODO: remove this function when all functionalities are implemented-
    #   argument parsing was moved to click in cli.py
    parser = argparse.ArgumentParser(
        description="Query an Open Data analysis record and download all"
        " index files needed for the analysis."
    )
    parser._action_groups.pop()
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "-r",
        "--record",
        type=int,
        help="Input the record id number for the Open Data"
        " analysis you want to query.",
    )

    args = parser.parse_args()
    input_record_id = args.record

    base_record_id = verify_recid(input_record_id)
    record_api = get_recid_api(base_record_id)
    dataset_links = get_datasets(record_api)
    dataset_ids = dataset_convert_to_ids(dataset_links)
    foo(base_record_id, dataset_ids)


if __name__ == "__main__":
    main()
