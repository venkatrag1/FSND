"use strict";

// ** Global variables and data
var map;

var neighbourhoodData = {
        title: 'Santa Clara',
        position: {
            lat: 37.354057,
            lng: -121.972395
}};

var markerData = [
    {
        title: "Children's Discovery Museum",
        position: {
            lat: 37.326755,
            lng: -121.89252
        }
    },
    {
        title: "Tech Museum of Innovation",
        position: {
            lat: 37.33149,
            lng: -121.890236
        }
    },
    {
        title: "Happy Hollow Park & Zoo",
        position: {
            lat: 37.325745,
            lng: -121.861383
        }
    },
    {
        title: "Palo Alto Junior Museum & Zoo",
        position: {
            lat: 37.41756,
            lng: -122.107222
        }
    },
    {
        title: "Bounce-A-Rama",
        position: {
            lat: 37.414779,
            lng: -121.894808
        }
    },
];

var markers = [];

// ** End global variables