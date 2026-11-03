---
url: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/03_basicmodel.html
title: 'Chapter 3: Models And Basic Fields'
fetched_at: '2026-11-03T00:50:29Z'
license: CC BY-SA 4.0
license_url: https://creativecommons.org/licenses/by-sa/4.0/
---

# Chapter 3: Models And Basic Fields {#chapter-3-models-and-basic-fields}

At the end of the previous chapter, we were able to create an Odoo module. However, at this point it is still an empty shell which doesn’t allow us to store any data. In our real estate module, we want to store the information related to the properties (name, description, price, living area…) in a database. The Odoo framework provides tools to facilitate database interactions.

Before moving forward in the exercise, make sure the `estate` module is installed, i.e. it must appear as ‘Installed’ in the Apps list.

> Warning
>
> Do not use mutable global variables.
>
> A single Odoo instance can run several databases in parallel within the same python process. Distinct modules might be installed on each of these databases, therefore we cannot rely on global variables that would be updated depending on installed modules.

## Object-Relational Mapping {#object-relational-mapping}

**Reference**: the documentation related to this topic can be found in the Models API.

> Note
>
> **Goal**: at the end of this section, the table `estate_property` should be created:
>
> ```
> $ psql -d rd-demo
> rd-demo=# SELECT COUNT(*) FROM estate_property;
> count
> -------
>     0
> (1 row)
> ```

A key component of Odoo is the [ORM](https://en.wikipedia.org/wiki/Object-relational_mapping) layer. This layer avoids having to manually write most [SQL](https://en.wikipedia.org/wiki/SQL) and provides extensibility and security services2.

Business objects are declared as Python classes extending `Model`, which integrates them into the automated persistence system.

Models can be configured by setting attributes in their definition. The most important attribute is `_name`, which is required and defines the name for the model in the Odoo system. Here is a minimum definition of a model:

```python
from odoo import models

class TestModel(models.Model):
    _name = "test_model"
```

This definition is enough for the ORM to generate a database table named `test_model`. By convention all models are located in a `models` directory and each model is defined in its own Python file.

Take a look at how the `crm_recurring_plan` table is defined and how the corresponding Python file is imported:

1. The model is defined in the file `crm/models/crm_recurring_plan.py` (see [here](https://github.com/odoo/odoo/blob/e80911aaead031e7523173789e946ac1fd27c7dc/addons/crm/models/crm_recurring_plan.py#L1-L9))
2. The file `crm_recurring_plan.py` is imported in `crm/models/__init__.py` (see [here](https://github.com/odoo/odoo/blob/e80911aaead031e7523173789e946ac1fd27c7dc/addons/crm/models/__init__.py#L15))
3. The folder `models` is imported in `crm/__init__.py` (see [here](https://github.com/odoo/odoo/blob/e80911aaead031e7523173789e946ac1fd27c7dc/addons/crm/__init__.py#L5))

> Exercise
>
> Define the real estate properties model.
>
> Based on example given in the CRM module, create the appropriate files and folder for the `estate_property` table.
>
> When the files are created, add a minimum definition for the `estate.property` model.

Any modification of the Python files requires a restart of the Odoo server. When we restart the server, we will add the parameters `-d` and `-u`:

```bash
$ ./odoo-bin --addons-path=addons,../enterprise/,../tutorials/ -d rd-demo -u estate
```

`-u estate` means we want to upgrade the `estate` module, i.e. the ORM will apply database schema changes. In this case it creates a new table. `-d rd-demo` means that the upgrade should be performed on the `rd-demo` database. `-u` should always be used in combination with `-d`.

During the startup you should see the following warnings:

```
...
WARNING rd-demo odoo.models: The model estate.property has no _description
...
WARNING rd-demo odoo.modules.loading: The model estate.property has no access rules, consider adding one...
...
```

If this is the case, then you should be good! To be sure, double check with `psql` as demonstrated in the **Goal**.

> Exercise
>
> Add a description.
>
> Add a `_description` to your model to get rid of one of the warnings.

## Model fields {#model-fields}

**Reference**: the documentation related to this topic can be found in the Fields API.

Fields are used to define what the model can store and where they are stored. Fields are defined as attributes in the model class:

```python
from odoo import fields, models

class TestModel(models.Model):
    _name = "test_model"
    _description = "Test Model"

    name = fields.Char()
```

The `name` field is a `Char` which will be represented as a Python unicode `str` and a SQL `VARCHAR`.

### Types {#types}

> Note
>
> **Goal**: at the end of this section, several basic fields should have been added to the table `estate_property`:
>
> ```
> $ psql -d rd-demo
>
> rd-demo=# \d estate_property;
>                                             Table "public.estate_property"
>     Column       |            Type             | Collation | Nullable |                   Default
> --------------------+-----------------------------+-----------+----------+---------------------------------------------
> id                 | integer                     |           | not null | nextval('estate_property_id_seq'::regclass)
> create_uid         | integer                     |           |          |
> create_date        | timestamp without time zone |           |          |
> write_uid          | integer                     |           |          |
> write_date         | timestamp without time zone |           |          |
> name               | character varying           |           |          |
> description        | text                        |           |          |
> postcode           | character varying           |           |          |
> date_availability  | date                        |           |          |
> expected_price     | double precision            |           |          |
> selling_price      | double precision            |           |          |
> bedrooms           | integer                     |           |          |
> living_area        | integer                     |           |          |
> facades            | integer                     |           |          |
> garage             | boolean                     |           |          |
> garden             | boolean                     |           |          |
> garden_area        | integer                     |           |          |
> garden_orientation | character varying           |           |          |
> Indexes:
>     "estate_property_pkey" PRIMARY KEY, btree (id)
> Foreign-key constraints:
>     "estate_property_create_uid_fkey" FOREIGN KEY (create_uid) REFERENCES res_users(id) ON DELETE SET NULL
>     "estate_property_write_uid_fkey" FOREIGN KEY (write_uid) REFERENCES res_users(id) ON DELETE SET NULL
> ```

There are two broad categories of fields: ‘simple’ fields, which are atomic values stored directly in the model’s table, and ‘relational’ fields, which link records (of the same or different models).

Simple field examples are `Boolean`, `Float`, `Char`, `Text`, `Date` and `Selection`.

> Exercise
>
> Add basic fields to the Real Estate Property table.
>
> Add the following basic fields to the table:
>
> | Field | Type |
> |---|---|
> | name | Char |
> | description | Text |
> | postcode | Char |
> | date_availability | Date |
> | expected_price | Float |
> | selling_price | Float |
> | bedrooms | Integer |
> | living_area | Integer |
> | facades | Integer |
> | garage | Boolean |
> | garden | Boolean |
> | garden_area | Integer |
> | garden_orientation | Selection |
>
> The `garden_orientation` field must have 4 possible values: ‘North’, ‘South’, ‘East’ and ‘West’. The selection list is defined as a list of tuples, see [here](https://github.com/odoo/odoo/blob/b0e0035b585f976e912e97e7f95f66b525bc8e43/addons/crm/report/crm_activity_report.py#L31-L34) for an example.

When the fields are added to the model, restart the server with `-u estate`

```bash
$ ./odoo-bin --addons-path=addons,../enterprise/,../tutorials/ -d rd-demo -u estate
```

Connect to `psql` and check the structure of the table `estate_property`. You’ll notice that a couple of extra fields were also added to the table. We will revisit them later.

### Common Attributes {#common-attributes}

> Note
>
> **Goal**: at the end of this section, the columns `name` and `expected_price` should be not nullable in the table `estate_property`:
>
> ```bash
> rd-demo=# \d estate_property;
>                                             Table "public.estate_property"
>     Column       |            Type             | Collation | Nullable |                   Default
> --------------------+-----------------------------+-----------+----------+---------------------------------------------
> ...
> name               | character varying           |           | not null |
> ...
> expected_price     | double precision            |           | not null |
> ...
> ```

Much like the model itself, fields can be configured by passing configuration attributes as parameters:

```python
name = fields.Char(required=True)
```

Some attributes are available on all fields, here are the most common ones:

**string (str, default: field’s name)**

The label of the field in UI (visible by users).

**required (bool, default: False)**

If `True`, the field can not be empty. It must either have a default value or always be given a value when creating a record.

**help (str, default: '')**

Provides long-form help tooltip for users in the UI.

**index (bool, default: False)**

Requests that Odoo create a [database index](https://use-the-index-luke.com/sql/preface) on the column.

> Exercise
>
> Set attributes for existing fields.
>
> Add the following attributes:
>
> | Field | Attribute |
> |---|---|
> | name | required |
> | expected_price | required |
>
> After restarting the server, both fields should be not nullable.

### Automatic Fields {#automatic-fields}

**Reference**: the documentation related to this topic can be found in Automatic fields.

You may have noticed your model has a few fields you never defined. Odoo creates a few fields in all models1. These fields are managed by the system and can’t be written to, but they can be read if useful or necessary:

**id (Id)**

The unique identifier for a record of the model.

**create_date (Datetime)**

Creation date of the record.

**create_uid (Many2one)**

User who created the record.

**write_date (Datetime)**

Last modification date of the record.

**write_uid (Many2one)**

User who last modified the record.

Now that we have created our first model, let’s add some security!

#### `1` {#autofields}

it is possible to disable the automatic creation of some fields

#### `2` {#rawsql}

writing raw SQL queries is possible, but requires caution as this bypasses all Odoo authentication and security mechanisms.
