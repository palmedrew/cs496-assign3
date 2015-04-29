from google.appengine.ext import ndb

class Model(ndb.Model):
  def to_dict(self):
    d = super(Model, self).to_dict()
    d['key'] = self.key.id()
    return d
    

class Category(Model):
  name = ndb.StringProperty(required=True)
  items = ndb.KeyProperty(kind="Item", repeated=True)
  def to_dict(self):
    d = super(Category, self).to_dict()
    d['items'] = [i.id() for i in d['items']]
    return d
  
class Item(Model):
  name = ndb.StringProperty(required=True)
  category = ndb.KeyProperty(kind="Category")
  places = ndb.KeyProperty(kind="Place", repeated=True)
  def to_dict(self):
    d = super(Item, self).to_dict()
    d['places'] = [rep.id() for rep in d['places']]
    d['category'] = d['category'].id() if d['category'] is not None else None
    return d
  
  
class Place(Model):
  name = ndb.StringProperty(required=True)
  items = ndb.KeyProperty(kind="Item", repeated=True)
  geocode = ndb.GeoPtProperty(required=True)
  def to_dict(self):
    d = super(Place, self).to_dict()
    d['items'] = [rep.id() for rep in d['items']]
    d['geocode'] = d['geocode'].__repr__()
    return d