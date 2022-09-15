/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* eslint-disable */
// copy/paste

(function () {
    'use strict';

    // Function to test if Intersection Observer is supported
    var supportsInsersectionObserver = (function () {
        return (
            'IntersectionObserver' in window &&
            'IntersectionObserverEntry' in window &&
            'intersectionRatio' in window.IntersectionObserverEntry.prototype
        );
    })();

    // Check for support
    if (
        supportsInsersectionObserver &&
        window.NodeList &&
        NodeList.prototype.forEach
    ) {
        setTimeout(function () {
            var observer = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        // trigger animation by adding relevant class with animation styles
                        if (entry.isIntersecting) {
                            console.log('intersecting');
                            var privacyModuleTag = document.querySelector(
                                "a[href='#private-mode'].c-module-tag"
                            );
                            var isPrivateModeSection =
                                privacyModuleTag.parentNode ===
                                entry.target.parentNode.parentNode;

                            entry.target.classList.add('animate-pop-in');
                            if (isPrivateModeSection) {
                                var background =
                                    entry.target.querySelector(
                                        '.c-browser-content'
                                    );
                                background.classList.add('mzp-t-dark');
                            }

                            // remove observer after triggering animation
                            observer.unobserve(entry.target);
                        }
                    });
                },
                { threshold: 0.4 }
            );

            // add observers
            document
                .querySelectorAll('.c-browser:not(.t-color-switch)')
                .forEach(function (element) {
                    observer.observe(element);
                });
        }, 200);
    }
})();
