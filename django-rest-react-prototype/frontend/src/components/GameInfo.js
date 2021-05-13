import React, {Component} from "react";
import Cookies from "js-cookie";

// Game Infographic component with optional price and optional deal information
export class GameInfo extends Component {
  constructor(props) {
    super(props);
    this.state = { tags: '' };
    this.like = this.like.bind(this);
  }

  componentDidMount() {
    // get tags from either category, props.tags, or the url in that order of
    // priority, depending on what we have.
    if (this.props.category != undefined) {
      // prefer category if we have it
      this.setState({tags: [this.props.category]});
    } else if (this.props.tags != undefined) {
      // use tags if we have them
      this.setState({tags: this.props.tags});
    } else {
      // get the genres using game steam ID
      //const gameID = "57690"; // TODO: extract ID from url
      //Trying to extract gameID from this.props.url
      console.log(this.props.url);
      var steam_url = this.props.url;
      //https://store.steampowered.com/app/{id}/othershit
      var steam_gameID = steam_url.split('/')[4]
      console.log(steam_gameID);
      const gameID = steam_gameID;

      fetch("https://store.steampowered.com/api/appdetails?appids=" + gameID)
        .then(res => res.json()).then(json => {
          const tags = json[gameID].data.genres.map(obj => obj.description);
          this.setState({tags: tags});
        });
    }
  }


  // handle a like request
  like(e) {
    e.preventDefault();
    const address =
      window.location.protocol + "//" + window.location.host + "/";
    const csrftoken = Cookies.get('csrftoken');

    fetch(address + 'current_user/')
      .then(res => {
        return res.json();
      })
      .then(json => {
        if (json.username) {
          fetch(address + 'steamid/')
            .then(res => {
              return res.json();
            })
            .then(steamid => {
              console.log('steamid:', steamid);
              const data = {
                tags: this.state.tags,
                steamid: steamid
              }

              fetch(address + 'like/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(data)
              });
            });
        }
      })
    ;
  };

  render() {
    // display appropriate info if this is a deal
    const isDeal = this.props.price_cut != undefined;

    // display appropriate info if we have the price
    const hasPrice = this.props.price != undefined;

    return (
      <div className="col-md-4 product-grid">
      <h5 className="text-center">{this.props.title}</h5>
        <img src={this.props.art} alt="" className="w-100" />

        { hasPrice &&
          ( isDeal
          ? <h5 className="text-center">NOW {this.props.currency}{this.props.price} {this.props.price_cut} OFF </h5>
          : <h5 className="text-center">PRICE {this.props.currency}{this.props.price}</h5>
          )
        }

      <a href={this.props.url} className="btn buy">BUY NOW</a>
      <button onClick={this.like}>Like</button>
      </div>
    );
  }

}
