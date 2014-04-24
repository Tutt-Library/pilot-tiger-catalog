=================================================
Engineering Assumptions in the Semantic Datastore
=================================================
by Jeremy Nelson


The `Catalog Pull Platform`_ tries to balance descriptive expressiveness in
the representation of entities, artifacts, and relationships with effective and
efficient data-structures in the design and implementation of the semantic 
datastore.


Normalization with JSON
-----------------------


MARC, Schema.org, and BIBFRAME
------------------------------
The semantic datastore uses MongoDB to store JSON and JSON-LD documents of
the following vocabularies: MARC, Schema.org, and BIBFRAME but the design
is flexible enough to accommodate many other standards as well. 

BIBFRAME
--------
In the current design (without using Mongo sharding), a single MongoDB
client has a dedicated BIBFRAME database with the following collections:

* **Work** - All Creative Works and sub-types are stored in this collection.

* **Instance** - All Instance and sub-types are stored in this collection.

* **Person** - All Person Authorities stored in this collection

* **CoverArt** - All Cover Art annotations are stored in this collection. The
  thumbnail image are stored through MongoDB's `GridFS`_.

* **Annotation**
                
* **Organization**
                           
* **Title**

* **Topic**
          


MARC
----
In the single MongoDB instance model, all MARC records are stored in a MongoDB
database with bibliographic collection, a name authority collection, title 
authority collection, and subject authority collection.

Schema.org
----------


First draft April 2014

..  _Catalog Pull Platform: http://intro2libsys.info/catalog-pull-platform
..  _GridFS: http://docs.mongodb.org/manual/core/gridfs/
