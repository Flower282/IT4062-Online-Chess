import React, { useEffect, useState } from 'react'
import WithMoveValidation from "../integrations/WithMoveValidation.jsx";
import { Button, Icon, Input, Dropdown } from 'semantic-ui-react';
import { useLocation, useHistory } from 'react-router-dom';
import socket from '../SocketConfig';
import WinLostPopup from '../WinLostPopup.jsx';
import Parser from 'html-react-parser';

import '../css/ChessBoard.css'

function ChessBoard() {
	const location = useLocation()
	const history = useHistory()
	const locState = location.state
	const [game, setGame] = useState(locState?.game || {})
	const [orientation, setOrientation] = useState()
	const [disconnected, setDisconnected] = useState(false)
	const [resigned, setResigned] = useState(false)
	const [opponentResigned, setOpponentResigned] = useState(false)
	const [pieces, setPieces] = useState("neo")
	const [board, setBoard] = useState("green.svg")

	useEffect(() => {
		// Safety check: redirect to home if no game data
		if (!locState || !locState.game || !locState.game.id) {
			history.push('/home');
			return;
		}

		socket.emit("fetch", { id: locState.game.id })
		
		const handleFetch = ({ game }) => {
			console.log("RICEVUTO FETCH")
			
			setGame(game)
			setDisconnected(false)
			if (locState.username === game.players[0]) {
				setOrientation("white")
			}
			else {
				setOrientation("black")
			}
		}
		
		const handleDisconnected = () => {
			setDisconnected(true)
		}
		
		const handleResigned = () => {
			setOpponentResigned(true)
		}
		
		socket.on("fetch", handleFetch);
		socket.on("disconnected", handleDisconnected)
		socket.on("resigned", handleResigned)

		// Cleanup function
		return () => {
			socket.off("fetch", handleFetch)
			socket.off("disconnected", handleDisconnected)
			socket.off("resigned", handleResigned)
		}

	}, [locState.game.id, locState.username]);

	const handleResignClick = () => {
		socket.emit("resign", { id: game.id })
		setResigned(true)
		// Popup sẽ hiển thị và user phải bấm OK để quay về home
	}

	const displayMoves = () => {
		let moves = game.pgn.split(" ")
		let rows = "";
		for (let i = 1; i < moves.length; i += 3) {
			rows += `<tr class="${i % 2 === 0 ? "even-row" : "odd-row"}">` +
				`<td className="index"><span>${moves[i - 1]}</span></td>` +
				`<td className="white"><span>${moves[i]}</span></td>` +
				`<td className="black"><span>${moves[i + 1] ? moves[i + 1] : ""}</span></td>` +
				"</tr>"
		}

		return rows;
	}

	return (
		<div className="chess-game-container">
			<WinLostPopup 
				win={opponentResigned ? true : false} 
				lost={resigned ? true : false} 
				draw={false} 
				resigned={(opponentResigned || resigned) ? true : false} 
			/>

			<div className="chess-game-wrapper">
				{/* Left Column - Game Info (Move History) */}
				<div className="chess-info-column">
					<div className="chess-info-card">
					{/* Opponent Info */}
					<div className="player-info opponent-info">
						<div className="player-avatar">
							<Icon name='user circle' size='big' style={{ color: '#111827' }} />
						</div>
					<div className="player-details">
						<div className="player-name">
							{orientation === 'white' 
								? (game.playerInfo?.[1]?.fullname || game.players?.[1] || 'Waiting...') 
								: (game.playerInfo?.[0]?.fullname || game.players?.[0] || 'Waiting...')}
						</div>
							<div className="player-role">
								{orientation === 'white' ? 'Player 2 (Black)' : 'Player 1 (White)'}
							</div>
						</div>
							{disconnected && (
								<div className="disconnected-badge">
									<Icon name='warning circle' /> Offline
								</div>
							)}
						</div>

						{/* Move History */}
						<div className="moves-section">
							<div className="section-header">
								<Icon name='list' />
								<span>Lịch sử nước đi</span>
							</div>
							<div className="moves-list">
								<table className="moves-table">
									<tbody>
										{Parser(displayMoves())}
									</tbody>
								</table>
							</div>
						</div>

					{/* Current Player Info */}
					<div className="player-info current-player-info">
						<div className="player-avatar">
							<Icon name='user circle' size='big' style={{ color: '#4CAF50' }} />
						</div>
					<div className="player-details">
						<div className="player-name">
							{orientation === 'white' 
								? (game.playerInfo?.[0]?.fullname || game.players?.[0] || locState.username) 
								: (game.playerInfo?.[1]?.fullname || game.players?.[1] || locState.username)}
						</div>
							<div className="player-role">
								{orientation === 'white' ? 'Player 1 (White)' : 'Player 2 (Black)'}
							</div>
							<div className="player-badge">Bạn</div>
						</div>
					</div>						{/* Game Controls */}
						<div className="game-controls">
							<Button 
								className="control-button resign-button"
								onClick={handleResignClick}
								fluid
							>
								<Icon name='flag' /> Xin thua
							</Button>

							<Button 
								className="control-button refresh-button"
								onClick={() => socket.emit("fetch", { id: locState.game.id })}
								fluid
							>
								<Icon name='refresh' /> Làm mới
							</Button>

							<Dropdown 
								text='Tùy chỉnh giao diện' 
								fluid
								button
								className='control-button settings-dropdown'
							>
								<Dropdown.Menu>
									<Dropdown.Item>
										<Dropdown text='Kiểu quân cờ' pointing='left'>
											<Dropdown.Menu>
												<Dropdown.Item onClick={() => setPieces("classic")}>Classic</Dropdown.Item>
												<Dropdown.Item onClick={() => setPieces("light")}>Light</Dropdown.Item>
												<Dropdown.Item onClick={() => setPieces("neo")}>Neo</Dropdown.Item>
												<Dropdown.Item onClick={() => setPieces("tournament")}>Tournament</Dropdown.Item>
												<Dropdown.Item onClick={() => setPieces("newspaper")}>Newspaper</Dropdown.Item>
												<Dropdown.Item onClick={() => setPieces("ocean")}>Ocean</Dropdown.Item>
												<Dropdown.Item onClick={() => setPieces("8bit")}>8-Bit</Dropdown.Item>
											</Dropdown.Menu>
										</Dropdown>
									</Dropdown.Item>
									<Dropdown.Item>
										<Dropdown text='Màu bàn cờ' pointing='left'>
											<Dropdown.Menu>
												<Dropdown.Item onClick={() => setBoard("brown.svg")}>Brown</Dropdown.Item>
												<Dropdown.Item onClick={() => setBoard("blue.svg")}>Blue</Dropdown.Item>
												<Dropdown.Item onClick={() => setBoard("green.svg")}>Green</Dropdown.Item>
												<Dropdown.Item onClick={() => setBoard("wood4.jpg")}>Wood</Dropdown.Item>
												<Dropdown.Item onClick={() => setBoard("newspaper.png")}>Newspaper</Dropdown.Item>
												<Dropdown.Item onClick={() => setBoard("leather.jpg")}>Leather</Dropdown.Item>
												<Dropdown.Item onClick={() => setBoard("metal.jpg")}>Metal</Dropdown.Item>
											</Dropdown.Menu>
										</Dropdown>
									</Dropdown.Item>
								</Dropdown.Menu>
							</Dropdown>
						</div>

						{/* Game ID */}
						<div className="game-id-section">
							<span className="game-id-label">Game ID:</span>
							<span className="game-id-value">{game.id}</span>
							<Icon 
								name='copy outline' 
								className="copy-icon"
								onClick={() => navigator.clipboard.writeText(game.id)}
								title="Copy Game ID"
							/>
						</div>
					</div>
				</div>

				{/* Right Column - Chess Board */}
				<div className="chess-board-column">
					<div className="chess-board-card">
						<WithMoveValidation 
							id={game.id} 
							pgn={game.pgn} 
							orientation={orientation} 
							pieces={pieces} 
							board={board} 
						/>
					</div>
				</div>
			</div>
		</div>
	);
}

export default ChessBoard;
