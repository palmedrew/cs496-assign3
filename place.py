import webapp2
from google.appengine.ext import ndb
import db_models
import json

class Place(webapp2.RequestHandler):
  def post(self):
    """ Creates a place entity
    
    POST Body Variables:
    name - Required.
    geocode - Required 
    items[] - item entity key id
    
    """
    
    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status)
      return
    
    name = self.request.get('name', None)
    geocode = self.request.get('geocode', None)
    items = self.request.get_all('items[]')
    pk = ndb.Key(db_models.Place, self.app.config.get('default-group'))
    ipk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
    curr_item_keys_id = None
    
    if geocode:
      geocode = ndb.GeoPt(str(geocode))
    
    # start checks
    if not name:
      self.response.set_status(400, "Invalid request, name Required")
      self.response.write(self.response.status)
      return   
    if not geocode:
      self.response.set_status(400, "Invalid request, geocode Required")
      self.response.write(self.response.status)
      return

    # name and geocode combination is unique? assume that geocode is correct
    q = db_models.Place.query(ancestor=pk)
    # q_name = q.filter(db_models.Place.name == name)
    # geo_results = q_name.fetch(projection=[ db_models.Place.geocode, db_models.Place.name ])
    geo_results = q.fetch(projection=[ db_models.Place.geocode, db_models.Place.name ])
    if geo_results:
      '''
      if geocode in geo_results:
        self.response.set_status(409, "Place Name/Geocode: " + name + "/" + geocode + " already used")
        self.response.write(self.response.status)
        return
      '''
      for gn in geo_results:
        if (gn.name == name and gn.geocode == geocode):
          self.response.set_status(409, "Place Name/Geocode: " + name + "/" + geocode.__repr__() + " already used")
          self.response.write(self.response.status)
          return
    
    if items:
      curr_item_keys_id = [ it.id() for it in db_models.Item.query(ancestor=ipk).fetch(keys_only=True)]
      for it in items:
        if it not in curr_item_keys_id:
          self.response.set_status(404, "Item: KeyID: " + it + " not in current list of items")
          self.response.write(self.response.status)
          return
          
          
    new_place = db_models.Place(parent=pk)
    new_place.name = name
    new_place.geocode = geocode      
    new_place.items = [ ndb.Key(db_models.Item, it, parent=ipk) for it in items ]
      
    pkey = new_place.put()
    
    for it_id in items:
      it_ent = db_models.Item.get_by_id(str(it_id), parent=ipk)
      it_ent.places.append(pkey)
      it_ent.put()
      
    out = new_place.to_dict()
    self.response.write(json.dumps(out))
    return


  def get(self, **kwargs):
    """ Queries category entity
    
    Get Body Variables:
    none -> returns keys of all item entities
    
    place id -> returns info on that item entity
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
    
    pk = ndb.Key(db_models.Place, self.app.config.get('default-group'))  
    q = db_models.Place.query(ancestor=pk)
    keys = q.fetch(keys_only=True)
    if 'id' not in kwargs:     
      results = { 'keys':[x.id() for x in keys]}
      self.response.write(json.dumps(results))
    elif ( int(kwargs['id']) in [ x.id() for x in keys]):
      out = db_models.Place.get_by_id(int(kwargs['id']), parent=pk).to_dict()
      self.response.write(json.dumps(out))
    else:
      self.response.set_status(404, "Place Key: " + kwargs['id'] + " does not exist")
      self.response.write(self.response.status)
        
    return
      
  def put(self, **kwargs):
    """ Modifies item entity
    
    Get Body Variables:
    name - new name for Place entity
    geocode - GeoPt of new geocode
    add_item[] - item key id to add to items
    del_item[] - item key id to del from items
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
    
    name = self.request.get('name', None)
    geocode = self.request.get('geocode', None)
    add_item = self.request.get_all('add_item[]')
    del_item = self.request.get_all('del_item[]')
    pk = ndb.Key(db_models.Place, self.app.config.get('default-group'))
    ipk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
    all_item_key_id = None
    
    if geocode:
      geocode = ndb.GeoPt(str(geocode))
    
    # start checks
    if 'id' not in kwargs:
      self.response.set_status(400, "Invalid request, Item ID Required")
      self.response.write(self.response.status)
      return
      
    place = db_models.Place.get_by_id(int(kwargs['id']), parent=pk)
    if not place:
      self.response.set_status(404, "Place Not Found")
      self.response.write(self.response.status)
      return
  
    #if changing name or geocode, must check that name/gecode combo are unique
    if name or geocode:
      chk_name = name if name else place.name
      chk_geocode = geocode if geocode else place.geocode
      
      q = db_models.Place.query(ancestor=pk)
      geo_results = q.fetch(projection=[ db_models.Place.geocode, db_models.Place.name ])
      if geo_results:
        for gn in geo_results:
          if (gn.name == name and gn.geocode == geocode):
            self.response.set_status(409, "Place Name/Geocode: " + name + "/" + geocode.__repr__() + " already used")
            self.response.write(self.response.status)
            return
      
    if add_item or del_item:
    # get rid of any duplicates in add_pl and del_pl
      if add_item and del_item:
        for ai in add_item:
          if ai in del_item:
            del_item.remove(ai)
            add_item.remove(ai)
      q = db_models.Item.query(ancestor=ipk)
      all_item_key_id = [x.id() for x in q.fetch(keys_only=True)]  
     
      if add_item:
        for si_key_id in add_item:
          if si_key_id not in all_item_key_id:
            self.response.set_status(404, "AddItem: Key.id: " + si_key_id + " not found")
            self.response.write(self.response.status)
            return
      if del_item:
        for si_key_id in del_item:
          if si_key_id not in all_item_key_id:
            self.response.set_status(404, "DelItem: Key.id: " + si_key_id + " not found")
            self.response.write(self.response.status)
            return
    #end checks
    
    if name:
      place.name = name        
            
    if geocode:
      place.geocode = geocode   
    
    if add_item:
      for si_key_id in add_item:
        if ndb.Key(db_models.Item, str(si_key_id), parent=ipk) not in place.items:
          place.items.append(ndb.Key(db_models.Item, str(si_key_id), parent=ipk))
          tit = db_models.Item.get_by_id(str(si_key_id), parent=ipk)
          if place.key not in tit.places:
            tit.places.append(place.key)
            tit.put()
          
    if del_item:
      for si_key_id in del_item:
        if ndb.Key(db_models.Item, str(si_key_id), parent=ipk) in place.items:
          place.items.remove(ndb.Key(db_models.Item, str(si_key_id), parent=ipk))
          tit = db_models.Item.get_by_id(str(si_key_id), parent=ipk)
          if place.key in tit.places:
            tit.places.remove(place.key)
            tit.put()
          
    place.put()
    out = place.to_dict()
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
    
    pk = ndb.Key(db_models.Place, self.app.config.get('default-group'))
    place = db_models.Place.get_by_id(int(kwargs['id']), parent=pk)
    if not place:
      self.response.set_status(404, "Place Not Found")
      self.response.write(self.response.status)
      return
      
    # prior to deleting the place, remove place from item.places
    if place.items:
      item_list = ndb.get_multi(place.items)
      for it in item_list:
        if place.key in it.places:
          it.places.remove(place.key)
      ndb.put_multi(item_list)
    
    # delete the place
    place.key.delete()
    
    # see if gone
    q = db_models.Place.query(ancestor=pk)
    keys = q.fetch(keys_only=True)
    if ( int(kwargs['id']) not in [x.id() for x in keys]):
      self.response.set_status(200, "Place Deleted")
      self.response.write(self.response.status)
    else:
      self.response.set_status(500, "Server Error: CategoryID: " + kwargs['id'] + " Not Deleted")
      self.response.write(self.response.status)
    
    return

