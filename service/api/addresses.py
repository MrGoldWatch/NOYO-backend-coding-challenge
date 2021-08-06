import logging
import json
from datetime import datetime, timedelta

from flask import abort, jsonify
from webargs.flaskparser import use_args

from marshmallow import Schema, fields

from service.server import app, db
from service.models import AddressSegment
from service.models import Person


class GetAddressQueryArgsSchema(Schema):
    date = fields.Date(required=False, missing=datetime.utcnow().date())


class AddressSchema(Schema):
    class Meta:
        ordered = True

    street_one = fields.Str(required=True, max=128)
    street_two = fields.Str(max=128)
    city = fields.Str(required=True, max=128)
    state = fields.Str(required=True, max=2)
    zip_code = fields.Str(required=True, max=10)

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=False)


# there is an issue with this function
# it doenst return the latest address nor all the addresses
@app.route("/api/persons/<uuid:person_id>/address", methods=["GET"])
@use_args(GetAddressQueryArgsSchema(), location="querystring")
def get_address(args, person_id):
    person = Person.query.get(person_id)
    if person is None:
        abort(404, description="person does not exist")
    elif len(person.address_segments) == 0:
        abort(404, description="person does not have an address, please create one")

    # this is were the issue is
    # the pop() returns first, not latest or all
    # address_segment = person.address_segments.pop()

    # to get the latest added item
    address_segment = person.address_segments.pop()

    ##########################################################
    # attempt to return all the added addresses for a person #
    ##########################################################

    # temp = len(person.address_segments)
    # dict_items = []
    # counter = 0

    # addresses = person.address_segments

    # for address in addresses:
    # dict_items.append(jsonify(AddressSchema().dump(address)))
    # counter = counter + 1

    # for i in range(temp):
    # row_as_dict = person.address_segments.pop(i)
    # dict_items[i] = jsonify(AddressSchema().dump(row_as_dict))
    # counter = counter + 1

    return jsonify(AddressSchema().dump(address_segment))
    # return json.dumps(dict_items[0])


@app.route("/api/persons/<uuid:person_id>/address", methods=["PUT"])
@use_args(AddressSchema())
def create_address(payload, person_id):
    person = Person.query.get(person_id)
    if person is None:
        abort(404, description="person does not exist")
    # If there are no AddressSegment records present for the person, we can go
    # ahead and create with no additional logic.
    elif len(person.address_segments) == 0:
        address_segment = AddressSegment(
            street_one=payload.get("street_one"),
            street_two=payload.get("street_two"),
            city=payload.get("city"),
            state=payload.get("state"),
            zip_code=payload.get("zip_code"),
            start_date=payload.get("start_date"),
            person_id=person_id,
        )

    else:
        # TODO: Implementation
        #
        # If there are one or more existing AddressSegments, create a new AddressSegment -> done
        # that begins on the start_date provided in the API request and continues
        # into the future. If the start_date provided is not greater than most recent
        # address segment start_date, raise an Exception.
        # raise NotImplementedError()

        # implementation steps:
        # 1- initialize new AddressSegment
        # 2- get the old addresses with the person_id
        # 3- check the new start_date is after the previewly entered ones
        # 4- set the end_date of the latest address to the start_date of the new one
        # 5- sumbit the new AddressSegment to the db

        # create a new AddressSegment
        # with values from the payload object
        address_segment = AddressSegment(
            street_one=payload.get("street_one"),
            street_two=payload.get("street_two"),
            city=payload.get("city"),
            state=payload.get("state"),
            zip_code=payload.get("zip_code"),
            start_date=payload.get("start_date"),
            person_id=person_id,
        )

        # initializes a dictionary to keep track of all the persons address_segments start_date
        # gets the latest address segment
        # key:id - value:start_date
        person_addresses = {}

        # gets and sotores all the previews addresses for the person
        addresses = person.address_segments

        # parses through all addresses to check if provided_start_date always starts after previews start_date
        for address in addresses:
            # if the start_date provided is not greater than most recent address segment start_date, raise an Exception.
            if address.start_date > payload.get("start_date"):
                # return jsonify({"type": "conflict", "description": "start_date must be greater than start_date for previews records"}), 400
                msg = (
                    "start_date: "
                    + str(address.start_date)
                    + " must be greater than start_date for previews records: "
                    + str(payload.get("start_date"))
                )
                # 409 CONFLICT
                # The request could not be completed due to a conflict with the current state of the target resource.
                # This code is used in situations where the user might be able to resolve the conflict and resubmit the request.
                return {"result": "conflict", "msg": msg, "error": "409"}, 409
            else:
                # adding date as value to be able to find the latest one
                person_addresses[address.id] = address.start_date

        # gets the latest start_date's record ID
        max_date_id = max(person_addresses, key=person_addresses.get)

        # uses the latest start_date's record ID to get the record
        old_address_obj = AddressSegment.query.get(max_date_id)
        # changes the end_date for the record with latest start_date to provided_start_date
        old_address_obj.end_date = payload.get("start_date")

    # db add and commit was moved down since its done in both if and else statement above
    db.session.add(address_segment)
    db.session.commit()
    db.session.refresh(address_segment)
    return jsonify(AddressSchema().dump(address_segment))
