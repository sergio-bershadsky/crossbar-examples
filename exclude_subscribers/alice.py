from __future__ import print_function

import random
from os import environ, urandom
from os.path import exists
from functools import partial

from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp import cryptosign
from autobahn.wamp.types import PublishOptions


if not exists('alice.priv'):
    with open('alice.priv', 'wb') as f:
        f.write(urandom(32))


class Component(ApplicationSession):
    """
    """
    key = cryptosign.SigningKey.from_raw_key('alice.priv')

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")
        print("  authid: {}".format(details.authid))
        print("authrole: {}".format(details.authrole))

        def got_heartbeat(name, counter):
            print("hearbeat: {}: {}".format(name, counter))

        for name in ['alice', 'bob', 'carol', 'dave', 'erin']:
            yield self.subscribe(
                partial(got_heartbeat, name),
                'public.heartbeat.{}'.format(name),
            )

        counter = 0
        topic = 'public.heartbeat.alice'
        while True:
            print("publish '{}'".format(topic))
            self.publish(
                topic, counter,
                options=PublishOptions(
                    exclude_authid=['bob'],
                    exclude=12345,
                ),
            )
            if counter % 2:
                self.publish(
                    topic, u"to everyone with 'alpha' role",
                    options=PublishOptions(
                        eligible_authrole=['alpha'],
                        exclude_me=False,
                    ),
                )
            counter += 1
            yield sleep(3)

    def onConnect(self):
        extra = {
            'pubkey': self.key.public_key(),
            'channel_binding': 'tls-unique'
        }

        # now request to join ..
        self.join(self.config.realm,
                  authmethods=['cryptosign'],
                  authid='alice',
                  authextra=extra)

    def onChallenge(self, challenge):
        self.log.info("authentication challenge received: {challenge}", challenge=challenge)
        # alright, we've got a challenge from the router.

        # not yet implemented. check the trustchain the router provided against
        # our trustroot, and check the signature provided by the
        # router for our previous challenge. if both are ok, everything
        # is fine - the router is authentic wrt our trustroot.

        # sign the challenge with our private key.
        signed_challenge = self.key.sign_challenge(self, challenge)

        # send back the signed challenge for verification
        return signed_challenge


if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("AUTOBAHN_DEMO_ROUTER", u"ws://127.0.0.1:8080/ws"),
        u"crossbardemo",
    )
    print("Alice pubkey: {}".format(Component.key.public_key()))
    runner.run(Component)
