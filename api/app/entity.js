var _e = require('./helper')
var _u = require('underscore')

var async = require('async')

var user = require('./user')



// Return one entity with given id
exports.get = function(req, res) {
    var id = _e.object_id(req.params.id)
    if(!id) return res.json(404, { error: 'There is no entity ' + req.params.id })

    async.waterfall([
        function(callback) {
            _e.db(req.host, callback)
        },
        function(db, callback) {
            db.collection('entity').findOne({'_id': id}, callback)
        },
    ], function(err, item) {
        if(err) return res.json(500, { error: err.message })
        if(!item) return res.json(404, { error: 'There is no entity with id ' + req.params.id })

        if(item.sharing === 'public') return res.json({ result: item })

        user.user_id(req, function(err, entity_id) {
            if(err || !entity_id || (item.sharing === 'private' && !_.contains(item.viewer, entity_id))) {
                return res.json(403, { error: 'No rights to view entity ' + req.params.id })
            } else {
                return res.json({ result: item })
            }
        })
    })
}



//Return list of entities
exports.list = function(req, res) {
    var query = {}
    var limit = parseInt(req.query.limit) ? parseInt(req.query.limit) : 100
    var skip  = parseInt(req.query.page)  ? (parseInt(req.query.page) - 1) * limit  : 0

    if(req.query.definition) query['definition'] = req.query.definition
    if(req.query.query) {
        var q = []
        _u.each(_u.uniq(req.query.query.toLowerCase().split(' ')), function(s) {
            q.push(new RegExp(s, 'i'))
        })
        query['search.et'] = {'$all': q}
    }

    async.waterfall([
        function(callback) {
            user.user_id(req, callback)
        },
        function(user_id, callback) {
            if(user_id) {
                query['$or'] = [{viewer: user_id}, {sharing: {'$in': ['public', 'domain']}}]
            } else {
                query['sharing'] = 'public'
            }
            _e.db(req.host, callback)
        },
        function(db, callback) {
            async.series({
                explain: function(callback) {
                    db.collection('entity').find(query).skip(skip).limit(limit).explain(callback)
                },
                count: function(callback) {
                    db.collection('entity').find(query).count(callback)
                },
                items: function(callback) {
                    db.collection('entity').find(query).skip(skip).limit(limit).toArray(callback)
                },
            }, function(err, results) {
                if(err) return res.json(500, { error: err.message })

                res.json({
                    query: query,
                    skip: skip,
                    limit: limit,
                    count: results.count,
                    explain: results.explain,
                    result: results.items,
                })
            })
        },
    ])
}
