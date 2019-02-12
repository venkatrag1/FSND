"use strict";

// ** Map methods
function mapLoadError() {
    $('#map').html('<h3 class="text-center">Error fetching google maps</h3>');
}

function initMap() {
    //Initialize map, markers and infowindow and populate marker global array
    map = new google.maps.Map(document.getElementById('map'), {
      center: neighbourhoodData.position,
      zoom: 13
    });
    var largeInfoWindow = new google.maps.InfoWindow();
    var bounds = new google.maps.LatLngBounds();
    markerData.forEach(function (markerItem) {
        var marker = new google.maps.Marker({
            position: markerItem.position,
            map: map,
            title: markerItem.title,
            animation: google.maps.Animation.DROP,
        });
        markers.push(marker);
        marker.addListener('click', function () {
            bounceMarker(this);
            populateInfoWindow(this, largeInfoWindow);
        });
        bounds.extend(markerItem.position);
    });
    map.fitBounds(bounds);
}

// Bounce marker twice
function bounceMarker(marker) {
    // marker.setAnimation(4); // Pretty cool but undocumented and may break.
    marker.setAnimation(google.maps.Animation.BOUNCE);
    setTimeout( function () {
        marker.setAnimation(null);
    }, 1400);
}

// Take infowindow and marker as input and asynchronously update infowindow
// with AJAX data from Yelp API
function setInfoWindowContent(marker, infowindow) {
    var content = '';
    content += '<h5>' + marker.title + '</h5>';
    // Placeholder while loading
    infowindow.setContent(content + '<i> Loading Yelp data </i>');
    // Go through proxy since Yelp doesn't support JSONP and isn't CORS enabled
    var corsAnywhereURL = 'https://cors-anywhere.herokuapp.com/';
    var YELP_API_KEY = 'sPqzCGLnq98TBJ-rfxkgkbQqOI6WWXh6TGZNi2tzkidnqT892TUygHnI9Tq0BdGruxV3usj4YbG3v7gBcDF01r_HEwpA3lK0Jp3wWeSSFBsTZ21v23rI6qWOXbhVXHYx';
    var yelpBaseURL = 'api.yelp.com/v3/';

    var yelpAutoCompURL = corsAnywhereURL + yelpBaseURL + 'autocomplete' + '?text=' + marker.title +
        '&latitude=' + marker.getPosition().lat() + '&longitude=' + marker.getPosition().lng();

    var businessID = '';
    var idLookupSuccess = true;

    // First issue Autocomplete AJAX call to get business ID given name and lat/lng
    var $businessIDlookup = $.ajax({
            url: yelpAutoCompURL,
            type: 'GET',
            dataType: 'json',
            headers: {
                'Authorization': 'Bearer ' + YELP_API_KEY,
            },
            success: function(response) {
                try {
                    // Only thing we do here is set the businesss ID
                    businessID = response.businesses[0].id;
                } catch (err) {
                    // JSON parsing error
                    idLookupSuccess = false;
                }
            },
        }).fail (function () {
        content += '<div class="alert-warning">Error fetching business ID from Yelp</div>';
        infowindow.setContent(content);
    });

    // Use the business ID from previous call to issue business details AJAX call
    $businessIDlookup.done( function () {
        var yelpBusinessDetailsURL = corsAnywhereURL + yelpBaseURL +
            'businesses/' + businessID;
        if (idLookupSuccess == true) {
            $.ajax({
                url: yelpBusinessDetailsURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'Authorization': 'Bearer ' + YELP_API_KEY,
                },
                success: function (response) {
                    try {
                        // Get rating
                        content += '<p>Rating: ' + response.rating + '/5</p>';
                        // Open Now or not
                        if (response.hours[0].is_open_now) {
                            content += '<p class="text-success">Open Now</p>';
                        } else {
                            content += '<p class="text-danger">Closed</p>';
                        }
                        // Telephone number
                        content += '<a href="tel:' + response.phone + '">' +
                            response.phone + '</a><br/>';
                        var businessLink = 'https://www.yelp.com/biz/' + businessID;
                        content += '<a href="' + businessLink +
                            '"><img src="img/Yelp_burst_positive_RGB.png" height="35" width="35">' +
                            '<span>Read more on Yelp</span></a>';
                    } catch (err) {
                        content += '<div class="alert-warning">Cannot some business details from Yelp</div>';
                    }
                    infowindow.setContent(content);
                }
            }).fail(function () {
                content += '<div class="alert-warning">Error fetching business details from Yelp</div>';
                infowindow.setContent(content);
            });
        } else {
            // JSON parsing error
            content += '<div class="alert-warning">Cannot parse businessID from Yelp</div>';
            infowindow.setContent(content);
        }
    });
}

function populateInfoWindow(marker, infowindow) {
    if (infowindow.marker != marker) {
        infowindow.marker = marker;
        setInfoWindowContent(marker, infowindow);
        infowindow.open(map, marker);
        // Make sure the marker property is cleared if the infowindow is closed.
        infowindow.addListener('closeclick',function(){
        infowindow.marker = null;
        });
    }
}

// ** End map methods

// ** Knockout.js viewmodel

var ViewModel = function () {
    var self = this;
    this.places = ko.observableArray([]);
    // Places array holds the title and position in the marker global array for each place
    markerData.forEach( function (marker, index) {
        self.places.push({
            title: marker.title,
            index: index
        });
    });
    this.query = ko.observable('');
    this.search = function (value) {
    // remove all the current places, which removes them from the view
        self.places.removeAll();
        for(var x in markerData) {
          if(markerData[x].title.toLowerCase().indexOf(value.toLowerCase()) >= 0) {
            self.places.push({
                title: markerData[x].title,
                index: x
            });
            markers[x].setVisible(true);
          } else {
              markers[x].setVisible(false);
          }
        }
    };
    this.query.subscribe(this.search);

    // If marker is selected from list view, propagate it through the marker click path to get the bounce and infowindow
    this.selectMarker = function (selectedPlace) {
        var marker = markers[selectedPlace.index];
        google.maps.event.trigger(marker, 'click');
    };


};

// Bind viewmodel
ko.applyBindings(new ViewModel());