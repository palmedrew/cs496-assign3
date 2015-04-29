import webapp2
from google.appengine.ext import ndb
import db_models
import json

class Category(webapp2.RequestHandler):
 
  
  def post(self):
    """ Creates a category entity
    
    POST Body Variables:
    name - Required. 
    item[] - list of item entity keys
    
    """
    
    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status)
      return
    
    name = self.request.get('name', None)
    if not name:
      self.response.set_status(400, "Invalid request, name Required")
      self.response.write(self.response.status)
      return
    if name in [ cat.name for cat in db_models.Category.query(ancestor=ndb.Key(db_models.Category, self.app.config.get('default-group'))).fetch()]:
      self.response.set_status(409, "Category Name: " + name + " already used")
      self.response.write(self.response.status)
      return
    
    pk = ndb.Key(db_models.Category, self.app.config.get('default-group'))
    new_cat = db_models.Category(parent=pk)
    new_cat.name = name
    
    items = self.request.get_all('item[]')
    ipk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
    curr_item_keys_id = [it.id() for it in db_models.Item.query(ancestor=ipk).fetch(keys_only=True)]
    my_it_dic = {}
    old_cat_dic= {}
    if items:
      if not curr_item_keys_id:
        self.response.set_status(404, "NO ITEMS EXIST to be added")
        self.response.write(self.response.status)
        return
      for add_it in items:
        if add_it not in curr_item_keys_id:
          self.response.set_status(404, "Item: " + add_it + " not in current list of items")
          self.response.write(self.response.status)
          return
        my_it = db_models.Item.get_by_id(str(add_it), parent=ipk)
        if not my_it:
          self.response.set_status(404, "Item: " + add_it + " not FOUND")
          self.response.write(self.response.status)
          return
        if my_it.category:
          if add_it in old_cat_dic:
            old_cat_dic[str(add_it)].append(my_it.category)
          else:
            old_cat_dic[add_it] = [my_it.category]
        my_it_dic[str(add_it)] = my_it

        
    new_cat.items = [ ndb.Key(db_models.Item, it) for it in items ]
    
    new_cat_key = new_cat.put()

    # this part changes all the items to this category
    if my_it_dic:
      my_it_list = my_it_dic.values()
      for ch_it in my_it_list:
        ch_it.category = new_cat_key
      ndb.put_multi(my_it_list)
      
    # this part now removes all the old items from their previous categories
    if old_cat_dic:

      for k,v in old_cat_dic.items():
        old_catkey_ent = ndb.get_multi(v)
        for old_cat in old_catkey_ent:
          old_cat.items.remove(my_it_dic[k].key)
        ndb.put_multi(old_catkey_ent)
      
      
    out = new_cat.to_dict()
    self.response.write(json.dumps(out))
    return


  def get(self, **kwargs):
    """ Queries category entity
    
    Get Body Variables:
    none -> returns keys of all category entities
    
    category id -> returns info on that category entity
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
      
    q = db_models.Category.query(ancestor=ndb.Key(db_models.Category, self.app.config.get('default-group')))
    keys = q.fetch(keys_only=True)
    if 'id' not in kwargs:     
      results = { 'keys':[x.id() for x in keys]}
      self.response.write(json.dumps(results))
    elif ( int(kwargs['id']) in [ x.id() for x in keys]):
      #out = ndb.Key(db_models.Category, int(kwargs['id'])).get().to_dict()
      pk = ndb.Key(db_models.Category, self.app.config.get('default-group'))
      out = db_models.Category.get_by_id(int(kwargs['id']), parent=pk).to_dict()
      self.response.write(json.dumps(out))
    else:
      self.response.set_status(404, "Category Key: " + kwargs['id'] + " does not exist")
      self.response.write(self.response.status)
        
    return
      
  def put(self, **kwargs):
    """ Modifies category entity
    
    Get Body Variables:
    name - new name for entity
    add_item[] - item key id to add
    del_item[] - item key id to delete
    
    """

    if 'application/json' not in self.request.accept:
      self.response.set_status(406, "Not Acceptable, API only supports application/json MIME type")
      self.response.write(self.response.status) 
      return
    
    name = self.request.get('name', None)
    add_item = self.request.get_all('add_item[]')
    del_item = self.request.get_all('del_item[]')
    
    if 'id' not in kwargs:
      self.response.set_status(400, "Invalid request, Category ID Required")
      self.response.write(self.response.status)
      return
      
    #cat = ndb.Key(db_models.Category, int(kwargs['id'])).get()
    pk = ndb.Key(db_models.Category, self.app.config.get('default-group'))
    cat = db_models.Category.get_by_id(int(kwargs['id']), parent=pk)
    if not cat:
      self.response.set_status(404, "Category Not Found")
      self.response.write(self.response.status)
      return
        
    if name:
      if name in [ cat.name for cat in db_models.Category.query(ancestor=ndb.Key(db_models.Category, self.app.config.get('default-group'))).fetch()]:
        self.response.set_status(409, "Category Name: " + name + " already used")
        self.response.write(self.response.status)
        return
    cat.name = name
      
    if add_item or del_item:
      # get rid of any duplicates in add_item and del_item
      if add_item and del_item:
        for ai in add_item:
          if ai in del_item:
            del_item.remove(ai)
            add_item.remove(ai)
    
      ipk = ndb.Key(db_models.Item, self.app.config.get('default-group'))
      q = db_models.Item.query(ancestor=ipk)
      all_item_key_id = [x.id() for x in q.fetch(keys_only=True)] 
      if add_item:
        for si_key_id in add_item:
          if si_key_id not in all_item_key_id:
            self.response.set_status(404, "AddItem: Key.id: " + si_key_id + " not found")
            self.response.write(self.response.status)
            return
          elif ndb.Key(db_models.Item, si_key_id) not in cat.items:
            cat.items.append(ndb.Key(db_models.Item, si_key_id))
            my_it = db_models.Item.get_by_id(str(si_key_id), parent=ipk)
            my_it.category = cat.key
            my_it.put()
          
      if del_item:
        for si_key_id in del_item:
          if si_key_id not in all_item_key_id:
            self.response.set_status(404, "DelItem: Key.id: " + si_key_id + " not found")
            self.response.write(self.response.status)
            return
          elif ndb.Key(db_models.Item, si_key_id) in cat.items:
            cat.items.remove(ndb.Key(db_models.Item, si_key_id))
            my_it = db_models.Item.get_by_id(str(si_key_id), parent=ipk)
            my_it.category = None
            my_it.put()
          
    cat.put()
    out = cat.to_dict()
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
    
    #cat = ndb.Key(db_models.Category, int(kwargs['id'])).get()
    pk = ndb.Key(db_models.Category, self.app.config.get('default-group'))
    cat = db_models.Category.get_by_id(int(kwargs['id']), parent=pk)
    if not cat:
      self.response.set_status(404, "Category Key id: " + kwargs['id'] + " Not Found")
      self.response.write(self.response.status)
      return
      
    # prior to delete the category, set all Item in this category to have category=None
    if cat.items:
      item_list = ndb.get_multi(cat.items)
      for it in item_list:
        it.category = None
      ndb.put_multi(item_list)
    
    # delete the category
    cat.key.delete()
    
    # see if gone
    q = db_models.Category.query(ancestor=ndb.Key(db_models.Category, self.app.config.get('default-group')))
    keys = q.fetch(keys_only=True)
    if ( kwargs['id'] not in [x.id() for x in keys]):
      self.response.set_status(200, "Category Deleted")
      self.response.write(self.response.status)
    else:
      self.response.set_status(500, "Server Error: CategoryID: " + kwargs['id'] + " Not Deleted")
      self.response.write(self.response.status)
    
    return

