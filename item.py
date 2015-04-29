import webapp2
from google.appengine.ext import ndb
import db_models
import json

class Item(webapp2.RequestHandler):
  def post(self):
    """ Creates an item entity
    
    POST Body Variables:
    name - Required. 
    category - category entity key id
    places[] - place entity key id
    
    """
    
    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status)
      return
    
    name = self.request.get('name', None)
    category = self.request.get('category', None)
    places = self.request.get_all('places[]')
    
    if not name:
      self.response.set_status(400, "Invalid request, name Required")
      self.response.write(self.response.status)
      return
    # doing query/filter on item.name could also do as key.id
    if name in [ item.name for item in db_models.Item.query(ancestor=ndb.Key(db_models.Item, self.app.config.get('default-group'))).fetch()]:
      self.response.set_status(409, "Item Name: " + name + " already used")
      self.response.write(self.response.status)
      return
    pk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
    new_item = db_models.Item(parent=pk, id=name)
    new_item.name = name
    
    if category:
      cat_key = ndb.Key(db_models.Category, int(category))
      if not cat_key.get():
        self.response.set_status(404, "Category Key: " + category + " does not exist")
        self.response.write(self.response.status) 
        return
      new_item.category = cat_key
    else:
      new_item.category = None
    
    curr_pl_keys_id = None      
    if places:
      curr_pl_keys_id = [ pl.id() for pl in db_models.Place.query(ancestor=ndb.Key(db_models.Place, self.app.config.get('defualt-group'))).fetch(keys_only=True)]
      for pl in places:
        if pl not in curr_pl_keys_id:
          self.response.set_status(404, "Place: KeyID: " + pl + " not in current list of places")
          self.response.write(self.response.status)
          return
    new_item.places = [ ndb.Key(db_models.Place, pl) for pl in places ]
      
    key = new_item.put()
    out = new_item.to_dict()
    self.response.write(json.dumps(out))
    return


  def get(self, **kwargs):
    """ Queries category entity
    
    Get Body Variables:
    none -> returns keys of all item entities
    
    item id -> returns info on that item entity
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
      
    q = db_models.Item.query(ancestor=ndb.Key(db_models.Item, self.app.config.get('default-group')))
    keys = q.fetch(keys_only=True)
    if 'id' not in kwargs:     
      results = { 'keys':[x.id() for x in keys]}
      self.response.write(json.dumps(results))
    elif ( kwargs['id'] in [ x.id() for x in keys]):
      pk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
      # this doesn't appear to work for string id
      #out = ndb.Key(db_models.Item, kwargs['id']).get().to_dict()
      # this does?  go figure
      out = db_models.Item.get_by_id(kwargs['id'], parent=pk).to_dict()
      self.response.write(json.dumps(out))
    else:
      self.response.set_status(404, "Item Key: " + kwargs['id'] + " does not exist")
      self.response.write(self.response.status)
        
    return
      
  def put(self, **kwargs):
    """ Modifies item entity
    
    Get Body Variables:
    name - new name for Item entity
    category - key id of new category entity
    add_place[] - place key id to add to places
    del_place[] - place key id to del from places
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
    
    name = self.request.get('name', None)
    category = self.request.get('category', None)
    add_place = self.request.get_all('add_place[]')
    del_place = self.request.get_all('del_place[]')
    
    if 'id' not in kwargs:
      self.response.set_status(400, "Invalid request, Item ID Required")
      self.response.write(self.response.status)
      return
    pk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
    item = db_models.Item.get_by_id(kwargs['id'], parent=pk)  
    if not item:
      self.response.set_status(404, "Item Not Found")
      self.response.write(self.response.status)
      return
        
    if name:      # constraint name = key, so if change name, must make clone
      if name in [ x.id() for x in db_models.Item.query(ancestor=ndb.Key(db_models.Item, self.app.config.get('default-group'))).fetch(keys_only=True)]:
        self.response.set_status(409, "Item Name: " + name + " already used")
        self.response.write(self.response.status)
        return
      #clone    really should probably have a transaction here till end of name:
      nu_item = db_models.Item(parent=pk, id=name)
      nu_item.name = name
      nu_item.category = item.category
      nu_item.places = list(item.places)
      nu_item_key = nu_item.put()
      # redirect references within category and places
      cat = ndbKey(db_models.Category, item.category).get()
      cat.items.remove(item.key)
      cat.items.append(nu_item_key)
      cat.put()
      place_list = ndb.get_mulit(item.places)
      for tpl in place_list:
        tpl.items.remove(item.key)
        tpl.items.append(nu_item_key)
      ndb.put_multi(place_list)
      #delete old
      item.key.delete()
      item = nu_item_key.get()
      
    if category:
      nu_cat_key = ndb.Key(db_models.Category, int(category))
      nu_cat = nu_cat_key.get()
      if not nu_cat:
        self.response.set_status(404, "Category Key: " + category + " does not exist")
        self.response.write(self.response.status) 
        return
      if item.category is not None and int(category) != item.category.integer_id():
        old_cat = item.category.get()
        old_cat.items.remove(item.key)
        old_cat.put()
        nu_cat.items.append(item.key)
        nu_cat.put()       
      item.category = nu_cat_key
           
    if add_place or del_place:
      # get rid of any duplicates in add_pl and del_pl
      if add_place and del_place:
        for apl in add_place:
          if apl in del_place:
            del_place.remove(apl)
            add_place.remove(apl)
    
      q = db_models.Place.query(ancestor=ndb.Key(db_models.Place, self.app.config.get('default-group')))
      all_place_key_id = [x.id() for x in q.fetch(keys_only=True)] 
      if add_place:
        for sp_key_id in add_place:
          if sp_key_id not in all_place_key_id:
            self.response.set_status(404, "AddPlace: Key.id: " + sp_key_id + " not found")
            self.response.write(self.response.status)
            return
          elif ndb.Key(db_models.Place, sp_key_id) not in item.places:
            item.places.append(ndb.Key(db_models.Place, sp_key_id))
          
      if del_place:
        for sp_key_id in del_pl:
          if sp_key_id not in all_place_key_id:
            self.response.set_status(404, "DelPlace: Key.id: " + sp_key_id + " not found")
            self.response.write(self.response.status)
            return
          elif ndb.Key(db_models.Place, sp_key_id) in item.places:
            item.places.remove(ndb.Key(db_models.Place, sp_key_id))
          
    item.put()
    out = item.to_dict()
    self.response.write(json.dumps(out))
    return
          

  def delete(self, **kwargs):
    """ Deletes category entity
    
    Delete Body Variables:
    none
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
    
    if 'id' not in kwargs:
      self.response.set_status(400, "Invalid request, Category ID Required")
      self.response.write(self.response.status)
      return
    
    pk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
    item = db_models.Item.get_by_id(kwargs['id'], parent=pk)
    
    if not item:
      self.response.set_status(404, "Item Key: " + kwargs['id'] + " Not Found")
      self.response.write(self.response.status)
      return
      
    # prior to deleting the item, remove item from category.items
    if item.category is not None:
      cat = item.category.get()
      if cat:
        cat.items.remove(item.key)
        cat.put()
    # prior to deleting item, remove from place.items
    if item.places:
      place_list = ndb.get_multi(item.places)
      for pl in place_list:
        pl.items.remove(item.key)
      ndb.put_multi(place_list)
    
    # delete the item
    item.key.delete()
    
    # see if gone
    q = db_models.Item.query(ancestor=ndb.Key(db_models.Item, self.app.config.get('default-group')))
    keys = q.fetch(keys_only=True)
    if ( kwargs['id'] not in [x.id() for x in keys]):
      self.response.set_status(200, "Category Deleted")
      self.response.write(self.response.status)
    else:
      self.response.set_status(500, "Server Error: CategoryID: " + kwargs['id'] + " Not Deleted")
      self.response.write(self.response.status)
    
    return

