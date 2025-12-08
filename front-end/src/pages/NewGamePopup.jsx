import React, { useState, useEffect } from 'react';
import Popup from 'reactjs-popup';
import { Redirect } from 'react-router-dom';
import "../css/NewGamePopup.css";
import socket from '../SocketConfig';
import { Checkbox, Button, Icon } from 'semantic-ui-react'

function NewGamePopup() {
	const [open, setOpen] = useState(undefined)
	const [username, setUsername] = useState('')
	const [game, setGame] = useState()
	const [redirect, setRedirect] = useState(false)
	const [loading, setLoading] = useState(false)

	const [ai, setAi] = useState('random')

	useEffect(() => {
		// Cleanup function to remove socket listeners when component unmounts
		return () => {
			socket.off("created")
			socket.off("createdComputerGame")
		}
	}, [])

	const handleSubmitMultiplayer = (e) => {
		e.preventDefault()

		// Remove previous listener to avoid duplicates
		socket.off("created")
		
		socket.emit("create", { username: username })
		setLoading(true)
		socket.once("created", ({ game }) => {
			setGame(game)
			setRedirect(true)
			setLoading(false)
		})
	}

	const handleSubmitComputer = (e) => {
		e.preventDefault()

		// Remove previous listener to avoid duplicates
		socket.off("createdComputerGame")

		socket.emit("createComputerGame", { username: username, ai: ai })
		setLoading(true)
		socket.once("createdComputerGame", ({ game }) => {
			setGame(game)
			setRedirect(true)
			setLoading(false)
		})
	}

	return (
		<Popup open={open} onClose={() => setOpen(undefined)} trigger={
			<button className="ui button" >
				New Game
			</button>
		} modal>
			<div className="modal">
				<h3 className="ui horizontal divider header">
					Choose a Username
				</h3>
				<div style={{ textAlign: "center" }}></div>
				<div className="ui form">
					<input value={username} onChange={e => { setUsername(e.target.value) }}></input>
					<br /><br />

					<div>
						<div className="inline fields equal width">
							<div className="field">
								Selected AI: <b>{ai}</b>
							</div>
							<div className="field">
								<Checkbox
									radio
									label='Random Moves'
									name='checkboxRadioGroup'
									value='random'
									checked={ai === 'random'}
									onChange={() => setAi('random')}
								/>
							</div>
							<div className="field">
								<Checkbox
									radio
									label='Stockfish 14'
									name='checkboxRadioGroup'
									value='stockfish'
									checked={ai === 'stockfish'}
									onChange={() => setAi('stockfish')}
								/>
							</div>
						</div>
					</div>
					<br />
					<button className={loading ? "ui loading button" : "ui button"} onClick={e => handleSubmitMultiplayer(e)} disabled={username === "" ? true : false}>
						Create Multiplayer Game
					</button>
					<br className='button-spacing' />
					<br className='button-spacing' />
					<button className={loading ? "ui loading button" : "ui button"} onClick={e => handleSubmitComputer(e)} disabled={username === "" ? true : false}>
						Create Game against Computer
					</button>
					{(redirect) ? <Redirect to={{ pathname: "/game", state: { username: username, game: game } }} /> : ''}
				</div>
			</div>

		</Popup >
	);
}

export default NewGamePopup;