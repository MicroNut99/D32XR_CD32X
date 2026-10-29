#include "doomdef.h"
#include "p_local.h"
#ifdef MARS
#include "mars.h"
#endif

VINT playertics, thinkertics, sighttics, basetics, latetics;
VINT tictics, drawtics;

boolean		gamepaused;
jagobj_t	*pausepic;
char		clearscreen = 0;

/*
===============================================================================

								THINKERS

All thinkers should be allocated by Z_Malloc so they can be operated on uniformly.  The actual
structures will vary in size, but the first element must be thinker_t.

Mobjs are similar to thinkers, but kept seperate for more optimal list
processing
===============================================================================
*/

thinker_t	thinkercap;	/* both the head and tail of the thinker list */
degenmobj_t		mobjhead;	/* head and tail of mobj list */
degenmobj_t		freemobjhead, freestaticmobjhead;	/* head and tail of free mobj list */
degenmobj_t		limbomobjhead;

//int			activethinkers;	/* debug count */
//int			activemobjs;	/* debug count */

/*
===============
=
= P_InitThinkers
=
===============
*/

void P_InitThinkers (void)
{
	thinkercap.prev = thinkercap.next  = &thinkercap;
	mobjhead.next = mobjhead.prev = (void *)&mobjhead;
	freemobjhead.next = freemobjhead.prev = (void *)&freemobjhead;
	freestaticmobjhead.next = freestaticmobjhead.prev = (void *)&freestaticmobjhead;
	limbomobjhead.next = limbomobjhead.prev = (void*)&limbomobjhead;
}

/*
===============
=
= P_SpawnThinker_
=
===============
*/

void *P_SpawnThinker_ (int size, int thinker_offset)
{
	void *p = Z_Malloc(size, PU_LEVSPEC);
	D_memset(p, 0, size);
	P_AddThinker((void *)((char *)p + thinker_offset));
	return p;
}

/*
===============
=
= P_AddThinker
=
= Adds a new thinker at the end of the list
=
===============
*/

void P_AddThinker (thinker_t *thinker)
{
	thinkercap.prev->next = thinker;
	thinker->next = &thinkercap;
	thinker->prev = thinkercap.prev;
	thinkercap.prev = thinker;
}


/*
===============
=
= P_RemoveThinker
=
= Deallocation is lazy -- it will not actually be freed until its
= thinking turn comes up
=
===============
*/

void P_RemoveThinker (thinker_t *thinker)
{
	thinker->function = (think_t)-1;
}

/*
===============
=
= P_RunThinkers
=
===============
*/

void P_RunThinkers (void)
{
	thinker_t	*currentthinker;
	
	//activethinkers = 0;
	
	currentthinker = thinkercap.next;
	while (currentthinker != &thinkercap)
	{
		if (currentthinker->function == (think_t)-1)
		{	/* time to remove it */
			currentthinker->next->prev = currentthinker->prev;
			currentthinker->prev->next = currentthinker->next;
			Z_Free (currentthinker);
		}
		else
		{
			if (currentthinker->function)
			{
				currentthinker->function (currentthinker);
			}
			//activethinkers++;
		}
		currentthinker = currentthinker->next;
	}
}

/*============================================================================= */

/* 
=================== 
= 
= P_RunMobjBase  
=
= Run stuff that doesn't happen every tick
=================== 
*/ 

void	P_RunMobjBase (void)
{
#ifdef JAGUAR
	extern	int p_base_start;
	 
	DSPFunction (&p_base_start);
#else
	P_RunMobjBase2 ();
#endif
}

/*============================================================================= */

/*
==============
=
= P_CheckCheats
=
==============
*/
 
void P_CheckCheats (void)
{
#ifdef JAGUAR
	int		buttons, oldbuttons;
	int 	warpmap;
	int		i;
	player_t	*p;

	for (i=0 ; i<MAXPLAYERS ; i++)
	{
		if (!playeringame[i])
			continue;
		buttons = ticbuttons[i];
		oldbuttons = oldticbuttons[i];
	
		if ( (buttons & BT_PAUSE) && !(oldbuttons&BT_PAUSE) )
			gamepaused ^= 1;
	}

	if (netgame)
		return;

	buttons = ticbuttons[0];
	oldbuttons = oldticbuttons[0];

	if ( (oldbuttons&BT_PAUSE) || !(buttons & BT_PAUSE ) )
		return;

	if (buttons&JP_NUM)
	{	/* free stuff */
		p=&players[0];
		for (i=0 ; i<NUMCARDS ; i++)
			p->cards[i] = true;			
		p->armorpoints = 200;
		p->armortype = 2;
		for (i=0;i<NUMWEAPONS;i++) p->weaponowned[i] = true;
		for (i=0;i<NUMAMMO;i++) p->ammo[i] = p->maxammo[i] = 500;
	}

	if (buttons&JP_STAR)
	{	/* godmode */
		players[0].cheats ^= CF_GODMODE;
	}
	warpmap = 0;
	if (buttons&JP_1) warpmap = 1;
	if (buttons&JP_2) warpmap = 2;
	if (buttons&JP_3) warpmap = 3;
	if (buttons&JP_4) warpmap = 4;
	if (buttons&JP_5) warpmap = 5;
	if (buttons&JP_6) warpmap = 6;
	if (buttons&JP_7) warpmap = 7;
	if (buttons&JP_8) warpmap = 8;
	if (buttons&JP_9) warpmap = 9;
	if (buttons&JP_A) warpmap += 10;
	else if (buttons&JP_B) warpmap += 20;
	
	if (warpmap>0 && warpmap < 27)
	{
		gamemaplump = G_LumpNumForMapNum(warpmap);
		gameaction = ga_warped;
	}
#elif defined(MARS)
	int i;
	int buttons;
	int oldbuttons;
	const int stuff_combo = BT_A | BT_B | BT_C | BT_UP;
	const int godmode_combo = BT_X | BT_Y | BT_Z | BT_UP;
	player_t* p;
	boolean automap = (players[consoleplayer].automapflags & AF_ACTIVE) != 0;
	extern VINT showAllThings;
	extern VINT showAllLines;

	if (netgame)
		return;
	if (!gamepaused)
		return;

	buttons = ticrealbuttons;
	oldbuttons = oldticrealbuttons;

	if ((buttons & stuff_combo) == stuff_combo 
		&& (oldbuttons & stuff_combo) != stuff_combo)
	{
		if (automap)
		{
			showAllThings ^= 1;
			return;
		}
		/* free stuff */
		p = &players[0];
		for (i = 0; i < NUMCARDS; i++)
			p->cards[i] = true;
		p->armorpoints = 200;
		p->armortype = 2;
		for (i = 0; i < NUMWEAPONS; i++)
		{
			if (i == wp_supershotgun)
			{
				if (sprites[SPR_SGN2].numframes == 0)
					continue;
			}
			p->weaponowned[i] = true;
		}
		for (i = 0; i < NUMAMMO; i++)
		{
			p->ammo[i] = p->maxammo[i] = 500;
		}
	}

	if ((buttons & godmode_combo) == godmode_combo 
		&& (oldbuttons & godmode_combo) != godmode_combo)
	{
		if (automap)
		{
			showAllLines ^= 1;
			return;
		}
		/* godmode */
		players[0].cheats ^= CF_GODMODE;
	}
#endif
}
  
void G_DoReborn (int playernum); 
void G_DoLoadLevel (void);

/*
=================
=
= P_Ticker
=
=================
*/

int		ticphase;

#ifdef MARS
#define frtc I_GetFRTCounter()
#else
#define frtc samplecount
#endif

int P_Ticker (void)
{
	int		start;
	int		ticstart;
	player_t	*pl;
	int 	playernum;

	if (demoplayback)
	{
		if (M_Ticker())
			return ga_exitdemo;
	}


	while (!I_RefreshLatched () )
	;		/* wait for refresh to latch all needed data before */
			/* running the next tick */

#ifdef JAGAUR
	while (DSPRead (&dspfinished) != 0xdef6)
	;		/* wait for sound mixing to complete */
#endif

    // bank-switch to the page with map data
	I_SetBankPage(segspage);

	gameaction = ga_nothing;

/* */
/* check for pause and cheats */
/* */
	P_CheckCheats ();
	
/* */
/* do option screen processing */
/* */

	for (playernum = 0, pl = players; playernum < MAXPLAYERS; playernum++, pl++)
		if (playeringame[playernum])
			O_Control(pl);

	if (gameaction != ga_nothing)
		return gameaction;

	/* */
	/* run player actions */
	/* */
	if (gamepaused)
		return 0;

	start = frtc;
	for (playernum = 0, pl = players; playernum < MAXPLAYERS; playernum++, pl++)
		if (playeringame[playernum])
		{
			if (pl->playerstate == PST_REBORN)
				G_DoReborn(playernum);
			AM_Control(pl);
			P_PlayerThink(pl);
		}
	playertics = frtc - start;

#ifdef THINKERS_30HZ
	start = frtc;
	P_RunThinkers();
	thinkertics = frtc - start;
#endif

	if (gametic != prevgametic)
	{
		ticstart = frtc;

#ifndef THINKERS_30HZ
		start = frtc;
		P_RunThinkers();
		thinkertics = frtc - start;
#endif

		start = frtc;
		P_CheckSights();
		sighttics = frtc - start;

		start = frtc;
		P_RunMobjBase();
		basetics = frtc - start;

		start = frtc;
		P_RunMobjLate();
		latetics = frtc - start;

		P_UpdateSpecials();

		P_RespawnSpecials();

		ST_Ticker();			/* update status bar */

		tictics = frtc - ticstart;
#ifdef CD32X_PLAYTEST
		PT_Tick();
#endif
	}

	return gameaction;		/* may have been set to ga_died, ga_completed, */
							/* or ga_secretexit */
}


/* 
============= 
= 
= DrawPlaque 
= 
============= 
*/ 
 
void DrawPlaque (jagobj_t *pl)
{
#ifndef MARS
	int			x,y,w;
	short		*sdest;
	byte		*bdest, *source;
	extern		int isrvmode;
	
	while ( !I_RefreshCompleted () )
	;

	bufferpage = (byte *)screens[!workpage];
	source = pl->data;
	
	if (isrvmode == 0xc1 + (3<<9) )
	{	/* 320 mode, stretch pixels */
		bdest = (byte *)bufferpage + 80*320 + (160 - pl->width);
		w = pl->width;
		for (y=0 ; y<pl->height ; y++)
		{
			for (x=0 ; x<w ; x++)
			{
				bdest[x*2] = bdest[x*2+1] = *source++;
			}
			bdest += 320;
		}
	}
	else
	{	/* 160 mode, draw directly */
		sdest = (short *)bufferpage + 80*160 + (80 - pl->width/2);
		w = pl->width;
		for (y=0 ; y<pl->height ; y++)
		{
			for (x=0 ; x<w ; x++)
			{
				sdest[x] = palette8[*source++];
			}
			sdest += 160;
		}
	}
#else
	clearscreen = 2;
#endif
}

/* 
============= 
= 
= DrawPlaque 
= 
============= 
*/ 
#ifndef MARS
void DrawSinglePlaque (jagobj_t *pl)
{
	int			x,y,w;
	byte		*bdest, *source;
	
	while ( !I_RefreshCompleted () )
	;

	bufferpage = (byte *)screens[!workpage];
	source = pl->data;
	
	bdest = (byte *)bufferpage + 80*320 + (160 - pl->width/2);
	w = pl->width;
	for (y=0 ; y<pl->height ; y++)
	{
		for (x=0 ; x<w ; x++)
			bdest[x] = *source++;
		bdest += 320;
	}
}
#endif


/* 
============= 
= 
= P_Drawer 
= 
= draw current display 
============= 
*/ 
 
 
void P_Drawer (void) 
{ 	
	boolean automapactive = (players[consoleplayer].automapflags & AF_ACTIVE) != 0;
	boolean optionsactive = (players[consoleplayer].automapflags & AF_OPTIONSACTIVE) != 0;
	static boolean o_wasactive, am_wasactive = false;
	viewdef_t vd_;

	vd = &vd_;

#ifdef MARS
	extern	boolean	debugscreenactive;

	drawtics = frtc;

	if ((!optionsactive && o_wasactive) || (!automapactive && am_wasactive))
		clearscreen = 2;

	if (clearscreen > 0) {
		int width = viewportWidth * (lowres ? 2 : 1);

		I_ResetLineTable();

		if (width == 320)
			I_ClearFrameBuffer();
		else
			DrawTiledBackground();

		I_DrawSbar();
		
		if (clearscreen == 2 || optionsactive)
			ST_ForceDraw();
		clearscreen--;
	}

	if (initmathtables)
	{
		R_InitMathTables();
		initmathtables--;
	}

	/* view the guy you are playing */
	R_RenderPlayerView(consoleplayer);
	/* view the other guy in split screen mode */
	if (splitscreen) {
		Mars_R_SecWait();
		R_RenderPlayerView(consoleplayer ^ 1);
	}

	ST_Drawer();

	Mars_R_SecWaitPause();

	if (automapactive)
		AM_Drawer();

	if (demoplayback)
		M_Drawer();
	if (optionsactive)
		O_Drawer();

	o_wasactive = optionsactive;
	am_wasactive = automapactive;

	drawtics = frtc - drawtics;

	if (debugscreenactive)
		I_DebugScreen();
#else
	if (optionsactive)
	{
		O_Drawer ();
	}
	else if (gamepaused && refreshdrawn)
		DrawPlaque (pausepic);
	else if (automapactive)
	{
		ST_Drawer ();
		AM_Drawer ();
		I_Update ();
	}
	else
	{
#ifdef JAGUAR
		ST_Drawer();
#endif
		R_RenderPlayerView(consoleplayer);
		clearscreen = 0;
	}
	/* assume part of the refresh is now running parallel with main code */
#endif
}
 
 
extern	 VINT		ticremainder[MAXPLAYERS];

void P_Start (void)
{
	int i;
	extern boolean canwipe;

	/* load a level */
	G_DoLoadLevel();

	AM_Start ();
#ifndef MARS
	S_RestartSounds ();
#endif
	for (i = 0; i < MAXPLAYERS; i++)
	{
		players[i].automapflags = 0;
		players[i].ticremainder = 0;
	}
	M_ClearRandom ();

	if (!demoplayback && !demorecording)
		if (!netgame || splitscreen)
			P_RandomSeed(I_GetTime());

	clearscreen = 2;
	canwipe = true;
}

void P_Stop (void)
{
	M_Stop();
	Z_FreeTags (mainzone);
}

void P_Update (void)
{
	int ticratebak;

	ticratebak = ticsperframe;

	if (viewportWidth >= 320 && ticsperframe < 3)
		ticsperframe = 3;

	I_Update();

	ticsperframe = ticratebak;
}

#ifdef CD32X_PLAYTEST
/* PLAYTEST (doomdef.h): the map played by itself, for ares */
pt_report_t pt_report;
static int pt_wait, pt_idx, pt_n;
static VINT pt_list[128];			/* small: the master SH2's stack is the RAM after the BSS */
#define PT_BUMP(a, i) do { if ((unsigned)(i) < sizeof(a)) { if ((a)[i] < 255) (a)[i]++; } } while (0)

static void PT_Place(mobj_t *mo, fixed_t x, fixed_t y, angle_t an)
{
	sector_t *sec;
	P_UnsetThingPosition(mo);
	mo->x = x;
	mo->y = y;
	P_SetThingPosition(mo);
	sec = SSEC_SECTOR(mo->subsector);
	mo->floorz = sec->floorheight;
	mo->ceilingz = sec->ceilingheight;
	mo->z = mo->floorz;
	mo->momx = mo->momy = mo->momz = 0;
	mo->angle = an;
}

static int PT_Alive(void)
{
	mobj_t *m;
	int n = 0;
	for (m = mobjhead.next; m != (void *)&mobjhead; m = m->next)
		if ((m->flags & MF_COUNTKILL) && m->health > 0)
			n++;
	return n;
}

static mobj_t *PT_Nth(int k)
{
	mobj_t *m;
	for (m = mobjhead.next; m != (void *)&mobjhead; m = m->next)
		if ((m->flags & MF_COUNTKILL) && m->health > 0 && k-- == 0)
			return m;
	return NULL;
}

/* the line kinds as D32XR's P_UseSpecialLine / P_CrossSpecialLine / P_ShootSpecialLine have them */
static int PT_LineKind(int s)
{
	static const uint8_t use[] = { 1, 7, 9, 11, 14, 15, 18, 20, 21, 23, 26, 27, 28, 29, 31, 32, 33, 34, 41, 42,
		43, 45, 49, 50, 51, 55, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 99, 101, 102, 103, 111, 112, 113,
		114, 115, 116, 117, 118, 122, 123, 127, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 0 };
	int i;
	if (s == 24 || s == 46 || s == 47)
		return 3;
	if (s == 48 || s == 142)
		return 0;			/* a scroller, not a trigger */
	for (i = 0; use[i]; i++)
		if (use[i] == s)
			return 1;
	return 2;
}

void P_NoiseAlert (player_t *player);

void PT_Tick(void)
{
	player_t *pl = &players[0];
	mobj_t *pmo = pl->mo, *m;
	int i;

	if (!pmo || !gamemapinfo)
		return;
	if (pt_report.magic != 0x50545354 || pt_report.map != gamemapinfo->mapNumber)
	{
		D_memset(&pt_report, 0, sizeof(pt_report));
		pt_report.magic = 0x50545354;	/* 'PTST' */
		pt_report.map = gamemapinfo->mapNumber;
		pt_report.phase = 1;
		pt_report.monsters0 = PT_Alive();
		pt_wait = 30;			/* the map's first 2 s: the start */
		pt_idx = 0;
	}
	pt_report.tic++;
	pt_report.killcount = pl->killcount;
	pt_report.secrets = pl->secretcount;
	if (pt_report.phase == 1)
		pmo->angle += ANG90 / 8;	/* a full turn in 32 tics */
	if (pt_wait > 0)
	{
		pt_wait--;
		return;
	}

	switch (pt_report.phase)
	{
	case 1:		/* the tour: up to 12 of the monsters' places, 3 s each, turning */
		{
			int stride = pt_report.monsters0 / 12 + 1;
			m = PT_Nth(pt_idx * stride);
			if (!m || pt_idx >= 12)
			{
				pt_report.phase = 2;
				pt_idx = 0;
				/* the Icon of Sin's spawners wake (in play: the player's shots), so its cubes fly during the kills */
				for (m = mobjhead.next; m != (void *)&mobjhead; m = m->next)
					if (m->type == MT_BOSSSPIT && m->state == S_BRAINEYE)
					{
						m->target = pmo;
						P_SetMobjState(m, mobjinfo[MT_BOSSSPIT].seestate);
						pt_report.eyes++;
					}
				break;
			}
			pt_report.point = pt_idx + 1;
			PT_Place(pmo, m->x, m->y, pmo->angle);
			P_NoiseAlert(pl);	/* as a shot there would: the monsters that hear it wake */
			pt_idx++;
			pt_wait = 48;
		}
		break;

	case 2:		/* every monster killed, by the player, 6 tics apart; 2 minutes at most */
		m = PT_Nth(0);
		if (!m || pt_report.tic > 30 + 12 * 49 + 1800)
		{
			pt_report.left = PT_Alive();
			pt_report.phase = 3;
			pt_idx = 0;
			pt_n = 0;
			for (i = 0; i < numlines && pt_n < (int)(sizeof(pt_list) / sizeof(pt_list[0])); i++)
			{
				int s = lines[i].special;
				if (!s || PT_LineKind(s) == 0 || s == 11 || s == 51 || s == 52 || s == 124)
					continue;	/* none, a scroller, the exits (phase 5) */
				pt_list[pt_n++] = i;
			}
			break;
		}
		{
			angle_t an = pmo->angle;
			fixed_t d = (m->radius + 40) << FRACBITS;
			PT_Place(pmo, m->x - FixedMul(d, finecosine(an >> ANGLETOFINESHIFT)),
				m->y - FixedMul(d, finesine(an >> ANGLETOFINESHIFT)), an);
			pt_report.point = pt_report.testkills + 1;
			PT_BUMP(pt_report.kills, m->type);
			pt_report.testkills++;
			P_DamageMobj(m, pmo, pmo, 10000);
			pt_wait = 6;
		}
		break;

	case 3:		/* every line special: from its front, facing it; 20 tics each */
		if (pt_idx >= pt_n)
		{
			pt_report.phase = 4;
			pt_idx = 0;
			pt_n = 0;
			for (i = 0; i < numsectors && pt_n < (int)(sizeof(pt_list) / sizeof(pt_list[0])); i++)
				if (sectors[i].special)
					pt_list[pt_n++] = i;
			break;
		}
		{
			line_t *ld = &lines[pt_list[pt_idx]];
			int s = ld->special, kind = PT_LineKind(s);
			fixed_t x1 = vertexes[ld->v1].x << FRACBITS, y1 = vertexes[ld->v1].y << FRACBITS;
			fixed_t x2 = vertexes[ld->v2].x << FRACBITS, y2 = vertexes[ld->v2].y << FRACBITS;
			fixed_t mx = x1 / 2 + x2 / 2, my = y1 / 2 + y2 / 2;
			fixed_t len = P_AproxDistance(x2 - x1, y2 - y1);
			fixed_t px = mx, py = my;
			if (len > 0)
			{
				px = mx + FixedDiv(FixedMul(y2 - y1, 24 << FRACBITS), len);
				py = my - FixedDiv(FixedMul(x2 - x1, 24 << FRACBITS), len);
			}
			pt_report.point = pt_idx + 1;
			if (s)
			{
				PT_Place(pmo, px, py, R_PointToAngle(px, py, mx, my));
				PT_BUMP(pt_report.lineact, s);
				pt_report.lines++;
				if (kind == 1)
				{
					if (P_UseSpecialLine(pmo, ld))
					{
						pt_report.linesused++;
						PT_BUMP(pt_report.lineused, s);
					}
				}
				else if (kind == 3)
					P_ShootSpecialLine(pmo, ld);
				else
					P_CrossSpecialLine(ld, pmo);
				pt_wait = 20;
			}
			pt_idx++;
		}
		break;

	case 4:		/* every special sector: stood in for 40 tics */
		if (pt_idx >= pt_n)
		{
			pt_report.phase = 5;
			break;
		}
		{
			int sn = pt_list[pt_idx];
			sector_t *sec = &sectors[sn];
			fixed_t cx = 0, cy = 0;
			int k, inside = -1;
			for (k = 0; k < sec->linecount; k++)
			{
				line_t *ld = &lines[sec->lines[k]];
				cx += (vertexes[ld->v1].x + vertexes[ld->v2].x) / 2;
				cy += (vertexes[ld->v1].y + vertexes[ld->v2].y) / 2;
			}
			if (sec->linecount)
			{
				cx = (cx / sec->linecount) << FRACBITS;
				cy = (cy / sec->linecount) << FRACBITS;
			}
			if (R_PointInSubsector(cx, cy)->sector == sn)
				inside = 1;
			for (k = 0; inside < 0 && k < sec->linecount; k++)
			{	/* else a point just inside one of its lines */
				line_t *ld = &lines[sec->lines[k]];
				fixed_t mx = ((vertexes[ld->v1].x + vertexes[ld->v2].x) / 2) << FRACBITS;
				fixed_t my = ((vertexes[ld->v1].y + vertexes[ld->v2].y) / 2) << FRACBITS;
				fixed_t tx = mx + (cx - mx) / 8, ty = my + (cy - my) / 8;
				if (R_PointInSubsector(tx, ty)->sector == sn)
					cx = tx, cy = ty, inside = 1;
			}
			pt_report.point = pt_idx + 1;
			if (inside > 0)
			{
				PT_BUMP(pt_report.secvisit, sec->special);
				PT_Place(pmo, cx, cy, pmo->angle);
				pt_report.sectors++;
				pt_wait = 40;
			}
			pt_idx++;
		}
		break;

	case 5:		/* the exit: the Icon of Sin killed, else an exit line set off */
		pt_report.phase = 6;
		pt_report.point = 0;
		for (m = mobjhead.next; m != (void *)&mobjhead; m = m->next)
			if (m->type == MT_BOSSBRAIN && m->health > 0)
				break;
		if (m != (void *)&mobjhead)
		{
			pt_report.exitspecial = -1;
			pt_report.exits++;
			P_DamageMobj(m, pmo, pmo, 10000);
			break;
		}
		for (i = 0; i < numlines; i++)
		{
			int s = lines[i].special;
			if (s == 52 || s == 124)
			{
				pt_report.exitspecial = s;
				pt_report.exits++;
				P_CrossSpecialLine(&lines[i], pmo);
				break;
			}
			if (s == 11 || s == 51)
			{
				pt_report.exitspecial = s;
				pt_report.exits++;
				P_UseSpecialLine(pmo, &lines[i]);
				break;
			}
		}
		if (!pt_report.exits)
			G_ExitLevel();
		break;

	default:
		break;
	}
}
#endif
