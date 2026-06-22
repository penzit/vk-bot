const API = {
  base: location.origin || (location.protocol + '//' + location.host),
  async get(path, params) {
    var qs = new URLSearchParams(params || {}).toString();
    var url = this.base + '/api' + path + (qs ? '?' + qs : '');
    console.log('[API GET]', url);
    var res = await fetch(url);
    if (!res.ok) throw new Error('API ' + res.status);
    return res.json();
  },
  async post(path, body) {
    var res = await fetch(this.base + '/api' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('API ' + res.status);
    return res.json();
  },
  async put(path, body) {
    var res = await fetch(this.base + '/api' + path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('API ' + res.status);
    return res.json();
  },
  async del(path) {
    var res = await fetch(this.base + '/api' + path, { method: 'DELETE' });
    if (!res.ok) throw new Error('API ' + res.status);
    return res.json();
  },
  getMasters: function(p) { return this.get('/masters', p); },
  getRecommendedMasters: function() { return this.get('/masters/recommended'); },
  getMaster: function(id) { return this.get('/masters/' + id); },
  getMasterReviews: function(id) { return this.get('/masters/' + id + '/reviews'); },
  getMasterCategories: function() { return this.get('/master_categories'); },
  getShopCategories: function() { return this.get('/shop_categories'); },
  getFoodCategories: function() { return this.get('/food_categories'); },
  getShops: function(p) { return this.get('/shops', p); },
  getRecommendedShops: function(p) { return this.get('/shops/recommended', p); },
  getShop: function(id) { return this.get('/shops/' + id); },
  getShopReviews: function(id) { return this.get('/shops/' + id + '/reviews'); },
  getFaqCategories: function() { return this.get('/faq_categories'); },
  getFaq: function(p) { return this.get('/faq', p); },
  getEmployers: function(p) { return this.get('/employers', p); },
  getRecommendedEmployers: function() { return this.get('/employers/recommended'); },
  getEmployer: function(id) { return this.get('/employers/' + id); },
  createReview: function(d) { return this.post('/reviews', d); },
  createShopReview: function(d) { return this.post('/shop_reviews', d); },
  registerMaster: function(d) { return this.post('/register', d); },
  registerShop: function(d) { return this.post('/register_shop', d); },
  registerEmployer: function(d) { return this.post('/register_employer', d); },
  submitMessage: function(d) { return this.post('/ads_request', d); },
  verifyMaster: function(d) { return this.post('/verify_master', d); },
  verifyShop: function(d) { return this.post('/verify_shop', d); },
  getAdsOffer: function() { return this.get('/ads_offer'); },
  updateMaster: function(id, d) { return this.put('/masters/' + id, d); },
  updateShop: function(id, d) { return this.put('/shops/' + id, d); },
  updateEmployer: function(id, d) { return this.put('/employers/' + id, d); },
  getMyItems: function(user_id) { return this.get('/my_items', { user_id: user_id }); },
  getOrderCategories: function() { return this.get('/order_categories'); },
  getUrgencyOptions: function() { return this.get('/order_urgency_options'); },
  createOrder: function(d) { return this.post('/orders', d); },
  getOrders: function(p) { return this.get('/orders', p); },
  getMyOrders: function(user_vk_id) { return this.get('/orders/my', { user_vk_id: user_vk_id }); },
  getPerformerOrders: function(vk_id) { return this.get('/orders/performer', { vk_id: vk_id }); },
  getOrder: function(id) { return this.get('/orders/' + id); },
  respondToOrder: function(order_id, d) { return this.post('/orders/' + order_id + '/respond', d); },
  declineOrder: function(order_id, performer_id) { return this.post('/orders/' + order_id + '/decline?performer_id=' + performer_id); },
  selectPerformer: function(order_id, response_id) { return this.post('/orders/' + order_id + '/select?response_id=' + response_id); },
  completeOrder: function(order_id, user_vk_id) { return this.post('/orders/' + order_id + '/complete?user_vk_id=' + user_vk_id); },
  cancelOrder: function(order_id, user_vk_id) { return this.post('/orders/' + order_id + '/cancel?user_vk_id=' + user_vk_id); },
  deleteOrder: function(order_id) { return this.del('/orders/' + order_id); },
  reviewOrder: function(order_id, d) { return this.post('/orders/' + order_id + '/review', d); },
  registerPerformer: function(d) { return this.post('/performers/register', d); },
  getPerformerProfile: function(vk_id) { return this.get('/performers/me', { vk_id: vk_id }); },
  updatePerformer: function(d) { return this.put('/performers/me', d); },
  setPerformerCategories: function(d) { return this.put('/performers/me/categories', d); },
  togglePerformer: function(vk_id) { return this.post('/performers/me/toggle', null, { vk_id: vk_id }); },
  getPerformer: function(id) { return this.get('/performers/' + id); },
  getPerformerReviews: function(id) { return this.get('/performers/' + id + '/reviews'); },
  getOrderStats: function() { return this.get('/orders/stats'); },
  expireOrders: function() { return this.get('/orders/expire/run'); },
};
