"""
Relmon request service. Automating relmon reports production.
"""

from flask import Flask
from flask.ext.restful import Api
from resources import resources
from RR_daemon import RelmonReportDaemon


app = Flask(__name__, static_url_path="")
api = Api(app)
api.add_resource(resources.Requests,
                 "/requests",
                 endpoint="requests")
api.add_resource(resources.Request,
                 "/requests/<int:request_id>",
                 endpoint="request")
api.add_resource(resources.Sample,
                 "/requests/<int:request_id>/categories/<string:category>/" +
                 "lists/<string:sample_list>/samples/<string:sample_name>",
                 endpoint="sample")
api.add_resource(resources.RequestLog,
                 "/requests/<int:request_id>/log",
                 endpoint="log")
api.add_resource(resources.RequestStatus,
                 "/requests/<int:request_id>/status",
                 endpoint="status")


if __name__ == '__main__':
    main_daemon = RelmonReportDaemon()
    main_daemon.start()
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=80)
