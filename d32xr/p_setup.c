/* P_main.c */

#include "doomdef.h"
#include "p_local.h"
#include "mars.h"

#if defined(CD32X) || defined(CD32X_AUX64)
/* CD32X: up to 64 extra lumps after a map's BLOCKMAP (sky, textures, flats): the converted
   PLUTONIA.WAD carries more of its own textures per map (tools/make_plutonia.py). The lump list
   ends at the first lump that is not one (the next map's marker), as before.
   CD32X_AUX64 (build.sh CARTCD=1 PLUTEX=1): the 32X+CD cartridge with PLUTEX's PLUTONIA.WAD, which
   may have more than 32 (a test build stopped at the 32nd: MAP01's slime came out as DOOM's blue water;
   the plain PLUTONIA.WAD has 21 at most) */
#define MAX_AUX_TEXTURES 64
#else
#define MAX_AUX_TEXTURES 32
#endif

VINT		numvertexes;
mapvertex_t	*vertexes;

VINT		numsegs;
seg_t		*segs;

VINT		numsectors;
sector_t	*sectors;

VINT		numsubsectors;
subsector_t	*subsectors;

VINT		numnodes;
node_t		*nodes;

VINT		numlines;
line_t		*lines;

VINT 		numlinetags;
VINT 		*linetags; // [HASH_SIZE]{line,tag,line,tag...}

VINT 		numsectortags;
VINT 		*sectortags; // [HASH_SIZE]{sector,tag,sector,tag...}

VINT		numsides;
side_t		*sides;

short		*blockmaplump;			/* offsets in blockmap are from here */
VINT		bmapwidth, bmapheight;	/* in mapblocks */
fixed_t		bmaporgx, bmaporgy;		/* origin of block map */
SPTR		*blocklinks;			/* for thing chains */

byte		*rejectmatrix;			/* for fast sight rejection */

VINT 		segspage = -1;

#ifdef CD32X
/* CD32X ROM maps: a map found in the IWAD (the game's ROM image in the RAM cart: tools/make_rommaps.py)
   keeps its vertexes, segs, nodes, reject and blockmap there in the engine's own big-endian form
   (segs in seg_t sorted as P_SortSegs does, nodes in node_t with the encoded boxes, the reject
   matrix packed as P_LoadRejectMatrix does), used in place: no RAM for them. Its sidedefs are
   side_t and its linedefs line_t + tags, copied into RAM (the game changes them); those, the
   things, sectors and subsectors may be compressed (the engine's LZSS). Its textures, flats
   and sky (the lumps after BLOCKMAP) are used in place too. Maps read from the CD are unchanged. */
#ifdef CD32X_ROMMAPS
static boolean P_RomMap(int lump)
{
	return W_IsIWad(lump);
}
#else
/* only the ROM map disc needs it (build_game.sh with IWAD=): the DOOM disc's program stays
   small enough for the 4 MB beside Fusion's IWAD */
#define P_RomMap(lump) false
#endif
#endif

#ifdef CD32X_PLUTEX
/* PLUTEX (below, P_SetupLevel): a map too big for the RAM keeps its read-only lumps (vertexes, segs,
   nodes, reject, blockmap in the engine's own form, as a ROM map's: tools/make_rommaps.py) in the
   cart block, written there when it loads and used in place */
static uint8_t *plutex_lvl[ML_BLOCKMAP + 1];
static int plutex_lvlbase = -1;
#define P_CartLevel(lump) (plutex_lvlbase >= 0 && (lump) >= plutex_lvlbase && (lump) - plutex_lvlbase <= ML_BLOCKMAP \
	? plutex_lvl[(lump) - plutex_lvlbase] : NULL)
#endif

mapthing_t	*deathmatchstarts, *deathmatch_p;

VINT		*validcount;			/* increment every time a check is made */

mapthing_t	playerstarts[MAXPLAYERS];

VINT		numthings;
spawnthing_t* spawnthings;

int16_t 	worldbbox[4];

/*
=================
=
= P_LoadVertexes
=
=================
*/

void P_LoadVertexes (int lump)
{
	byte		*data;
	int			i;
	mapvertex_t	*ml;
	mapvertex_t	*li;
	
	numvertexes = W_LumpLength (lump) / sizeof(mapvertex_t);
#ifdef CD32X_PLUTEX
	if (P_CartLevel(lump))
		vertexes = (void *)P_CartLevel(lump);	/* in the cart block: big-endian, used in place */
	else
#endif
#ifdef CD32X
	if (P_RomMap(lump))
		vertexes = W_POINTLUMPNUM(lump);	/* ROM map: big-endian, used in place */
	else
#endif
	{
	vertexes = Z_Malloc (numvertexes*sizeof(mapvertex_t) + 16,PU_LEVEL);
	vertexes = (void*)(((uintptr_t)vertexes + 15) & ~15); // aline on cacheline boundary
	data = W_GetLumpData(lump);

	ml = (mapvertex_t *)data;
	li = vertexes;
	for (i=0 ; i<numvertexes ; i++, li++, ml++)
	{
		li->x = LITTLESHORT(ml->x);
		li->y = LITTLESHORT(ml->y);
	}
	}

	worldbbox[BOXLEFT] = INT16_MAX;
	worldbbox[BOXRIGHT] = INT16_MIN;
	worldbbox[BOXBOTTOM] = INT16_MAX;
	worldbbox[BOXTOP] = INT16_MIN;

	li = vertexes;
	for (i=0 ; i<numvertexes ; i++, li++)
	{
		mapvertex_t *v = li;
		if (v->x < worldbbox[BOXLEFT])
			worldbbox[BOXLEFT] = v->x;
		if (v->x > worldbbox[BOXRIGHT])
			worldbbox[BOXRIGHT] = v->x;
		if (v->y < worldbbox[BOXBOTTOM])
			worldbbox[BOXBOTTOM] = v->y;
		if (v->y > worldbbox[BOXTOP])
			worldbbox[BOXTOP] = v->y;
	}
}


/*
=================
=
= P_LoadSegs
=
=================
*/

void P_LoadSegs (int lump)
{
	byte		*data;
	int			i;
	mapseg_t	*ml;
	seg_t		*li;
	int			linedef, side;

#ifdef USE_SMALL_LUMPS
	numsegs = W_LumpLength (lump) / sizeof(seg_t);

	// FIXME: this is strictly big-endian for now
	if (W_IsIWad(lump))
	{
		segs = W_POINTLUMPNUM(lump);
		return;
	}

	segs = Z_Malloc (numsegs*sizeof(seg_t)+16,PU_LEVEL);
	segs = (void*)(((uintptr_t)segs + 15) & ~15); // aline on cacheline boundary
	W_ReadLump(lump, segs);
	return;
#endif

#ifdef CD32X_PLUTEX
	if (P_CartLevel(lump))
	{
		numsegs = W_LumpLength (lump) / sizeof(seg_t);
		segs = (void *)P_CartLevel(lump);
		return;
	}
#endif
#ifdef CD32X
	if (P_RomMap(lump))
	{
		numsegs = W_LumpLength (lump) / sizeof(seg_t);
		segs = W_POINTLUMPNUM(lump);
		return;
	}
#endif
	numsegs = W_LumpLength (lump) / sizeof(mapseg_t);
	segs = Z_Malloc (numsegs*sizeof(seg_t)+16,PU_LEVEL);
	segs = (void*)(((uintptr_t)segs + 15) & ~15); // aline on cacheline boundary
	D_memset (segs, 0, numsegs*sizeof(seg_t));
	data = W_GetLumpData(lump);

	ml = (mapseg_t *)data;
	li = segs;
	for (i=0 ; i<numsegs ; i++, li++, ml++)
	{
		li->v1 = (unsigned)LITTLESHORT(ml->v1);
		li->v2 = (unsigned)LITTLESHORT(ml->v2);

		linedef = (unsigned)LITTLESHORT(ml->linedef);

		li->linedef = linedef;

		side = (unsigned)LITTLESHORT(ml->side);

		SEG_PACK(li, side);
	}
}


/*
=================
=
= P_LoadSubsectors
=
=================
*/

void P_LoadSubsectors (int lump)
{
	byte			*data;
	int				i;
	int 			count;
	mapsubsector_t	*ms;
	subsector_t		*ss;

#ifdef USE_SMALL_LUMPS
	int16_t 		*cn;
	int 			curline;

	numsubsectors = W_LumpLength (lump) / sizeof(int16_t);
	count = numsubsectors+1;
	subsectors = Z_Malloc (count*sizeof(subsector_t),PU_LEVEL);
	data = W_GetLumpData(lump);

	cn = (int16_t *)data;
	D_memset (subsectors,0, count*sizeof(subsector_t));

	if (!numsubsectors)
		return;

	curline = 0;
	ss = subsectors;
	for (i=0 ; i<numsubsectors ; i++, ss++, cn++)
	{
		count = BIGSHORT(*cn);
		ss->firstline = curline;
		curline += count;
	}

	ss->firstline = curline;
	return;
#endif

	numsubsectors = W_LumpLength (lump) / sizeof(mapsubsector_t);
	count = numsubsectors+1;
	subsectors = Z_Malloc (count*sizeof(subsector_t),PU_LEVEL);
	data = W_GetLumpData(lump);

	ms = (mapsubsector_t *)data;
	D_memset (subsectors,0, count*sizeof(subsector_t));

	if (!numsubsectors)
		return;

	ss = subsectors;
	for (i=0 ; i<numsubsectors ; i++, ss++, ms++)
	{
		count = LITTLESHORT(ms->numsegs);
		ss->firstline = LITTLESHORT(ms->firstseg);
	}

	--ss;
	(ss + 1)->firstline = ss->firstline + count;
}


/*
=================
=
= P_LoadSectors
=
=================
*/

void P_LoadSectors (int lump)
{
	byte			*data;
	int				i;
	mapsector_t		*ms;
	sector_t		*ss;
	int 			tag;
			
	numsectors = W_LumpLength (lump) / sizeof(mapsector_t);
	sectors = Z_Malloc (numsectors*sizeof(sector_t) + 16,PU_LEVEL);
	sectors = (void*)(((uintptr_t)sectors + 15) & ~15); // aline on cacheline boundary
	D_memset (sectors, 0, numsectors*sizeof(sector_t));
	data = W_GetLumpData(lump);
	numsectortags = 0;

	ms = (mapsector_t *)data;
	ss = sectors;
	for (i=0 ; i<numsectors ; i++, ss++, ms++)
	{
		int lightlevel, special;

		ss->floorheight = LITTLESHORT(ms->floorheight)<<FRACBITS;
		ss->ceilingheight = LITTLESHORT(ms->ceilingheight)<<FRACBITS;
		ss->floorpic = R_FlatNumForName(ms->floorpic);
		if (!D_strncasecmp (ms->ceilingpic,"F_SKY1",6) )
			*(int8_t *)&ss->ceilingpic = -1;
		else
		{
			ss->ceilingpic = R_FlatNumForName(ms->ceilingpic);
		}
		ss->thinglist = (SPTR)0;

		lightlevel = LITTLESHORT(ms->lightlevel);
		if (lightlevel < 0)
			lightlevel = 0;
		else if (lightlevel > 255)
			lightlevel = 255;
		ss->lightlevel = lightlevel;

		special = LITTLESHORT(ms->special);
		if (special < 0 || special > 255)
			special = 0;
		ss->special = special;

		tag = LITTLESHORT(ms->tag);
		if (tag != 0) {
			numsectortags++;
		}
	}

	// load tags into hash table

	if (!numsectortags)
		return;

	numsectortags = (numsectortags + LINETAGS_HASH_SIZE - 1) & ~(LINETAGS_HASH_SIZE - 1);
	sectortags = Z_Malloc(sizeof(*sectortags)*numsectortags*2, PU_LEVEL);
	D_memset(sectortags, -1, sizeof(*sectortags)*numsectortags*2);

	ms = (mapsector_t *)data;
	for (i=0 ; i<numsectors ; i++,  ms++)
	{
		tag = LITTLESHORT(ms->tag);
		if (tag) {
			P_SetSectorTag(i, tag);
		}
	}
}


/*
=================
=
= P_LoadNodes
=
=================
*/


static int P_EncodeBBoxSide(int16_t *b, int16_t *outerbbox, int pc, int nc)
{
	int length, unit;
	int nu, pu;

	length = outerbbox[pc] - outerbbox[nc] + 15;
	if (length < 16)
		return 0;
	unit = length / 16;

	// negative corner is increasing
	nu = 0;
	length = b[nc] - outerbbox[nc];
	if (length > 0) {
		nu = length / unit;
		if (nu > 15)
			nu = 15;
		b[nc] = outerbbox[nc] + nu * unit;
	}

	// positive corner is decreasing
	pu = 0;
	length = outerbbox[pc] - b[pc];
	if (length > 0) {
		pu = length / unit;
		if (pu > 15)
			pu = 15;
		b[pc] = outerbbox[pc] - pu * unit;
	}

	return (pu << 4) | nu;
}

// encodes bbox as the number of 1/16th units of parent bbox on each side
static int P_EncodeBBox(int16_t *cb, int16_t *outerbbox)
{
	int encbbox;
	encbbox = P_EncodeBBoxSide(cb, outerbbox, BOXRIGHT, BOXLEFT);
	encbbox <<= 8;
	encbbox |= P_EncodeBBoxSide(cb, outerbbox, BOXTOP, BOXBOTTOM);
	return encbbox;
}

static void P_EncodeNodeBBox_r(int nn, int16_t *bboxes, int16_t *outerbbox)
{
	int 		j;
	node_t 		*n;

	if (nn & NF_SUBSECTOR)
		return;

	n = nodes + nn;
	for (j=0 ; j<2 ; j++)
	{
		int16_t *bbox = &bboxes[nn*8+j*4];
		n->encbbox[j] = P_EncodeBBox(bbox, outerbbox);
		P_EncodeNodeBBox_r(n->children[j], bboxes, bbox);
	}
}

// set the world's bounding box
// recursively encode bounding boxes for all BSP nodes
static void P_EncodeNodesBBoxes(int16_t *bboxes)
{
	P_EncodeNodeBBox_r(numnodes-1, bboxes, worldbbox);
}

void P_LoadNodes (int lump)
{
	byte		*data;
	int			i,j,k;
	node_t		*no;
	mapnode_t 	*mn;
	int16_t 	*bboxes;

#ifdef USE_SMALL_LUMPS
	numnodes = W_LumpLength (lump) / sizeof(node_t);

	// FIXME: this is strictly big-endian for now
	if (W_IsIWad(lump))
	{
		int oldpage = 255;
		I_SetBankPage(oldpage);

		nodes = W_POINTLUMPNUM(lump);

		// re-use nodes from ROM if possible
		const int page = I_GetBankPage();
		if (page == oldpage)
		{
			// not in bank-switched area
			return;
		}

		if (segspage < 0 || page == segspage) {
			segspage = page;
			return;
		}
	}

	nodes = Z_Malloc (numnodes*sizeof(node_t) + 16,PU_LEVEL);
	nodes = (void*)(((uintptr_t)nodes + 15) & ~15); // aline on cacheline boundary
	W_ReadLump(lump, nodes);
	return;
#endif

#ifdef CD32X_PLUTEX
	if (P_CartLevel(lump))
	{
		numnodes = W_LumpLength (lump) / sizeof(node_t);
		nodes = (void *)P_CartLevel(lump);
		return;
	}
#endif
#ifdef CD32X
	if (P_RomMap(lump))
	{
		numnodes = W_LumpLength (lump) / sizeof(node_t);
		nodes = W_POINTLUMPNUM(lump);
		return;
	}
#endif
	numnodes = W_LumpLength (lump) / sizeof(*mn);
	data = W_GetLumpData(lump);
	nodes = Z_Malloc (numnodes*sizeof(node_t) + 16,PU_LEVEL);
	nodes = (void*)(((uintptr_t)nodes + 15) & ~15); // aline on cacheline boundary
	bboxes = (void *)I_FrameBuffer();

	mn = (mapnode_t *)data;
	no = nodes;
	for (i=0 ; i<numnodes ; i++, no++, mn++)
	{
		no->x = LITTLESHORT(mn->x);
		no->y = LITTLESHORT(mn->y);
		no->dx = LITTLESHORT(mn->dx);
		no->dy = LITTLESHORT(mn->dy);

		for (j=0 ; j<2 ; j++)
		{
			no->children[j] = LITTLESHORT(mn->children[j]);
			for (k=0 ; k<4 ; k++)
				bboxes[i*8+j*4+k] = LITTLESHORT(mn->bbox[j][k]);
		}
	}

	P_EncodeNodesBBoxes(bboxes);
}

/*
=================
=
= P_LoadThings
=
=================
*/

void P_LoadThings (int lump, boolean *havebossspit)
{
	byte			*data;
	int				i;
	mapthing_t		*mt;
	spawnthing_t	*st;
	int 			numthingsreal, numstaticthings;

	numthings = W_LumpLength (lump) / sizeof(mapthing_t);
	data = I_TempBuffer(numthings*sizeof(mapthing_t));
	W_ReadLump(lump, data);
	numthingsreal = 0;
	numstaticthings = 0;
	*havebossspit = false;

	I_SetBankPage(segspage);

	mt = (mapthing_t *)data;
	for (i=0 ; i<numthings ; i++, mt++)
	{
		mt->x = LITTLESHORT(mt->x);
		mt->y = LITTLESHORT(mt->y);
		mt->angle = LITTLESHORT(mt->angle);
		mt->type = LITTLESHORT(mt->type);
		mt->options = LITTLESHORT(mt->options);
	}

	if (netgame == gt_deathmatch)
	{
		spawnthings = Z_Malloc(numthings * sizeof(*spawnthings), PU_LEVEL);
		st = spawnthings;
		mt = (mapthing_t*)data;
		for (i = 0; i < numthings; i++, mt++)
		{
			st->x = mt->x, st->y = mt->y;
			st->angle = mt->angle;
			st->type = mt->type;
			st++;
		}
	}

	mt = (mapthing_t *)data;
	for (i=0 ; i<numthings ; i++, mt++)
	{
		switch (P_MapThingSpawnsMobj(mt))
		{
			case 0:
				break;
			case 1:
				if (mt->type == mobjinfo[MT_BOSSSPIT].doomednum)
					*havebossspit = true;
				numthingsreal++;
				break;
			case 2:
				numstaticthings++;
				break;
		}
	}

	// preallocate a few mobjs for puffs and projectiles
	numthingsreal += 40;
	P_PreSpawnMobjs(numthingsreal, numstaticthings);

	mt = (mapthing_t *)data;
	for (i=0 ; i<numthings ; i++, mt++)
		P_SpawnMapThing (mt, i);
}

/*
=================
=
= P_LoadLineDefs
=
= Also counts secret lines for intermissions
=================
*/

void P_LoadLineDefs (int lump)
{
	byte			*data;
	int				i;
	maplinedef_t	*mld;
	line_t			*ld;

#ifdef CD32X
	if (P_RomMap(lump))
	{
		/* a ROM map's linedefs: line_t[numlines] as the loader below leaves them, then the
		   lines' tags (int16_t[numlines]); maybe compressed (decoded into the temp buffer) */
		int16_t *tags;

		numlines = W_LumpLength (lump) / (sizeof(line_t) + sizeof(int16_t));
		lines = Z_Malloc (numlines*sizeof(line_t)+16,PU_LEVEL);
		lines = (void*)(((uintptr_t)lines + 15) & ~15); // aline on cacheline boundary
		data = W_GetLumpData(lump);
		D_memcpy (lines, data, numlines*sizeof(line_t));
		tags = (int16_t *)(data + numlines*sizeof(line_t));
		numlinetags = 0;
		for (i = 0; i < numlines; i++)
			if (tags[i])
				numlinetags++;
		if (!numlinetags)
			return;
		numlinetags = (numlinetags + LINETAGS_HASH_SIZE - 1) & ~(LINETAGS_HASH_SIZE - 1);
		linetags = Z_Malloc(sizeof(*linetags)*numlinetags*2, PU_LEVEL);
		D_memset(linetags, -1, sizeof(*linetags)*numlinetags*2);
		for (i = 0; i < numlines; i++)
			if (tags[i])
				P_SetLineTag(i, tags[i]);
		return;
	}
#endif
	numlines = W_LumpLength (lump) / sizeof(maplinedef_t);
	lines = Z_Malloc (numlines*sizeof(line_t)+16,PU_LEVEL);
	lines = (void*)(((uintptr_t)lines + 15) & ~15); // aline on cacheline boundary
	D_memset (lines, 0, numlines*sizeof(line_t));
	data = W_GetLumpData(lump);
	numlinetags = 0;

	mld = (maplinedef_t *)data;
	ld = lines;
	for (i=0 ; i<numlines ; i++, mld++, ld++)
	{
		int tag;

		ld->flags = LITTLESHORT(mld->flags);
		ld->special = LITTLESHORT(mld->special);
		tag = LITTLESHORT(mld->tag);
		ld->v1 = LITTLESHORT(mld->v1);
		ld->v2 = LITTLESHORT(mld->v2);

		ld->sidenum[0] = LITTLESHORT(mld->sidenum[0]);
		ld->sidenum[1] = LITTLESHORT(mld->sidenum[1]);

		if (tag)
			numlinetags++;

		// HACK HACK HACK
		// backwards compatibility with JagDoom specials
		// that use values typically reserved for Doom2 maps
		if (tag)
			continue;

		switch (ld->special)
		{
		case 99:
			/* Blue Skull Door Open */
			ld->special = 32;
			break;
		case 100:
			/* Red Skull Door Open */
			ld->special = 33;
			break;
		case 105:
			/* Yellow Skull Door Open */
			ld->special = 34;
			break;
		case 106:
			/* Blue Skull Door Raise */
		case 107:
			/* Red Skull Door Raise */
		case 108:
			/* Yellow Skull Door Raise */
			ld->special = ld->special - 80;
			break;
		}
	}

	// load tags into hash table

	if (!numlinetags)
		return;

	numlinetags = (numlinetags + LINETAGS_HASH_SIZE - 1) & ~(LINETAGS_HASH_SIZE - 1);
	linetags = Z_Malloc(sizeof(*linetags)*numlinetags*2, PU_LEVEL);
	D_memset(linetags, -1, sizeof(*linetags)*numlinetags*2);

	mld = (maplinedef_t *)data;
	for (i=0 ; i<numlines ; i++, mld++)
	{
		int tag = LITTLESHORT(mld->tag);
		if (tag) {
			P_SetLineTag(i, tag);
		}
	}
}


/*
=================
=
= P_LoadSideDefs
=
=================
*/

void P_LoadSideDefs (int lump)
{
	byte			*data;
	int				i;
	mapsidedef_t	*msd;
	side_t			*sd;

#ifndef MARS
	for (i=0 ; i<numtextures ; i++)
		textures[i].usecount = 0;
#endif	
#ifdef CD32X
	if (P_RomMap(lump))
	{
		/* a ROM map's sidedefs are side_t already (texture numbers looked up by the build) */
		numsides = W_LumpLength (lump) / sizeof(side_t);
		sides = Z_Malloc (numsides*sizeof(side_t)+16,PU_LEVEL);
		sides = (void*)(((uintptr_t)sides + 15) & ~15); // aline on cacheline boundary
		W_ReadLump (lump, sides);		/* maybe compressed */
		return;
	}
#endif
	numsides = W_LumpLength (lump) / sizeof(mapsidedef_t);
	sides = Z_Malloc (numsides*sizeof(side_t)+16,PU_LEVEL);
	sides = (void*)(((uintptr_t)sides + 15) & ~15); // aline on cacheline boundary
	D_memset (sides, 0, numsides*sizeof(side_t));
	data = W_GetLumpData(lump);

	msd = (mapsidedef_t *)data;
	sd = sides;
	for (i=0 ; i<numsides ; i++, msd++, sd++)
	{
		int rowoffset, textureoffset;
		textureoffset = LITTLESHORT(msd->textureoffset);
		rowoffset = LITTLESHORT(msd->rowoffset);
		sd->toptexture = R_TextureNumForName(msd->toptexture);
		sd->bottomtexture = R_TextureNumForName(msd->bottomtexture);
		sd->midtexture = R_TextureNumForName(msd->midtexture);
		sd->sector = LITTLESHORT(msd->sector);
		sd->rowoffset = rowoffset & 0xff;
		sd->textureoffset = (textureoffset & 0xfff) | ((rowoffset & 0x0f00) << 4);
#ifndef MARS
		textures[sd->toptexture].usecount++;
		textures[sd->bottomtexture].usecount++;
		textures[sd->midtexture].usecount++;
#endif
	}
}


/*
=================
=
= P_LoadRejectMatrix
=
=================
*/

void P_LoadRejectMatrix (int lump)
{
	int i, j;
	uint8_t *data, *out;
	int outsize;
	unsigned outbit, outbyte;

#ifdef CD32X_PLUTEX
	if (P_CartLevel(lump))
	{
		rejectmatrix = P_CartLevel(lump);	/* packed already */
		return;
	}
#endif
#ifdef CD32X
	if (P_RomMap(lump))
	{
		rejectmatrix = W_POINTLUMPNUM(lump);	/* packed already */
		return;
	}
#endif
	// compress the reject table, assuming it is symmetrical
	outsize = (numsectors + 1) * numsectors / 2;
	outsize = (outsize + 7) / 8;

	rejectmatrix = Z_Malloc (outsize,PU_LEVEL);
	D_memset(rejectmatrix, 0, outsize);
	data = W_GetLumpData(lump);

	outbit = 1;
	outbyte = 0;
	out = rejectmatrix;

	for (i = 0; i < numsectors; i++) {
		unsigned k = i*numsectors;
		unsigned bit = 1 << ((k + i) & 7);

		for (j = i; j < numsectors; j++) {
			unsigned bytenum = (k + j) / 8;

			if (data[bytenum] & bit)
			{
				out[outbyte] |= outbit;
			}

			bit <<= 1;
			if (bit > 0xff) {
				bit = 1;
			}

			outbit <<= 1;
			if (outbit > 0xff) {
				outbyte++;
				outbit = 1;
			}
		}
	}
}

/*
=================
=
= P_LoadBlockMap
=
=================
*/

void P_LoadBlockMap (int lump)
{
	int		i;
	int		count;

#ifdef CD32X_PLUTEX
	if (P_CartLevel(lump))
		blockmaplump = (void *)P_CartLevel(lump);	/* big-endian, in place */
	else
#endif
#ifdef CD32X
	if (P_RomMap(lump))
		blockmaplump = W_POINTLUMPNUM(lump);	/* big-endian, in place */
	else
#endif
	{
	blockmaplump = Z_Malloc (W_LumpLength (lump),PU_LEVEL);
	W_ReadLump (lump,blockmaplump);
	count = W_LumpLength (lump)/2;
	for (i=0 ; i<count ; i++)
		blockmaplump[i] = LITTLESHORT(blockmaplump[i]);
	}

	bmaporgx = blockmaplump[0]<<FRACBITS;
	bmaporgy = blockmaplump[1]<<FRACBITS;
	bmapwidth = blockmaplump[2];
	bmapheight = blockmaplump[3];

/* clear out mobj chains */
	count = sizeof(*blocklinks)* bmapwidth*bmapheight;
	blocklinks = Z_Malloc (count,PU_LEVEL);
	D_memset (blocklinks, 0, count);
}




/*
=================
=
= P_GroupLines
=
= Builds sector line lists and subsector sector numbers
= Finds block bounding boxes for sectors
=================
*/

void P_GroupLines (void)
{
	VINT		*linebuffer;
	int			i, total;
	sector_t	*sector;
	subsector_t	*ss;
	seg_t		*seg;
	line_t		*li;

	I_SetBankPage(segspage);

/* look up sector number for each subsector */
	ss = subsectors;
	for (i=0 ; i<numsubsectors ; i++, ss++)
	{
		int side;
		side_t *sidedef;
		line_t* linedef;

		seg = &segs[ss->firstline];
		linedef = &lines[SEG_UNPACK_LINEDEF(seg)];
		side = SEG_UNPACK_SIDE(seg);
		sidedef = &sides[linedef->sidenum[side]];
		if (side == 1)
		{
			// set the guard flag for the back side, otherwise it
			// may be set to -1 in the loop below
			linedef->flags |= ML_TWOSIDED;
		}
		ss->sector = sidedef->sector;
	}

	/* if the two-sided flag isn't set, set the back side to -1 */
	li = lines;
	for (i=0 ; i<numlines ; i++, li++)
	{
		if (li->sidenum[1] >= 0 && !(li->flags & ML_TWOSIDED)) {
			li->sidenum[1] = -1;
		}
		li->flags &= ~ML_TWOSIDED;
	}

/* count number of lines in each sector */
	li = lines;
	total = 0;
	for (i=0 ; i<numlines ; i++, li++)
	{
		sector_t *front = LD_FRONTSECTOR(li);
		sector_t *back = LD_BACKSECTOR(li);

		front->linecount++;
		total++;
		if (back && back != front)
		{
			back->linecount++;
			total++;
		}
	}
	
/* build line tables for each sector	 */
	linebuffer = Z_Malloc (total*sizeof(*linebuffer), PU_LEVEL);
	sector = sectors;
	for (i=0 ; i<numsectors ; i++, sector++)
	{
		sector->lines = linebuffer;
		linebuffer += sector->linecount;
		sector->linecount = 0;
	}

	li = lines;
	for (i=0 ; i<numlines ; i++, li++)
	{
		sector_t *front = LD_FRONTSECTOR(li);
		sector_t *back = LD_BACKSECTOR(li);

		front->lines[front->linecount++] = i;
		if (back && back != front)
		{
			back->lines[back->linecount++] = i;
		}
	}
}

/*============================================================================= */


/*
=================
=
= P_LoadingPlaque
=
=================
*/

void P_LoadingPlaque (void)
{
#ifndef MARS
	jagobj_t	*pl;

	pl = W_CacheLumpName ("loading", PU_STATIC);	
	DrawPlaque (pl);
	Z_Free (pl);
#endif
}	

/*============================================================================= */

static void P_isortsegs(seg_t * segs, int len)
{
	int i, j;
	for (i = 1; i < len; i++)
	{
		seg_t t;
		t.linedef = segs[i].linedef;
		t.v1 = segs[i].v1;
		t.v2 = segs[i].v2;
		for (j = i - 1; j >= 0; j--)
		{
			if (segs[j].linedef <= t.linedef)
				break;
			segs[j+1].linedef = segs[j].linedef;
			segs[j+1].v1 = segs[j].v1;
			segs[j+1].v2 = segs[j].v2;
		}
		segs[j+1].linedef = t.linedef;
		segs[j+1].v1 = t.v1;
		segs[j+1].v2 = t.v2;
	}
}

// Sorts segments in subsectors by linedef in ascending order
static void P_SortSegs(void)
{
	int i;

	for (i = 0; i < numsubsectors; i++)
	{
		subsector_t *sub = &subsectors[i];
		int count = SSEC_NUMLINES(sub);
		int firstline = sub->firstline;
		P_isortsegs(&segs[firstline], count);
	}
}

#ifdef CD32X_PLUTEX
/* PLUTEX (build.sh PLUTEX=1): the cart's memory is RAM (the RAM cart, the EverDrive's PSRAM), so the
   68000 can write the game's own image while it runs. tools/make_cartblk.py moved the base game's
   textures and flats that Plutonia never uses itself into one block at the IWAD's end (CARTBLK: its
   offset and length), and tools/make_game.py --cart-iwad put Plutonia's pictures that go there in each
   map's extra lumps, with CARTMAP (the first extra lump, big-endian: 'CMAP', count, then per lump its
   place among the extras and its offset in the IWAD). Those are written into the block (the 68000's
   command 16, src-md/crt0.s cart_write) and drawn from there like the base game's own; the others go
   to RAM as before. A picture's size is its own (its header): a donor name of another size takes it
   for the map. CARTREC says 'PLTX' while the block holds Plutonia's pictures; any other game puts the
   block back first (PLUTONIA.WAD's CARTPOOL: its own bytes) - also after a reset, as the cart keeps
   its memory. */
#define PLUTEX_DIRTY 0x504C5458			/* 'PLTX' */
static int8_t plutex_ok = -1;			/* -1: not looked yet, 0: no block, 1: the block */
static uint32_t plutex_blk, plutex_blkiwad, plutex_blklen, plutex_recoff;
static int plutex_cmap = -1;			/* CARTMAP's place among the extra lumps */
static struct { VINT tex, w, h; } plutex_sized[MAX_AUX_TEXTURES];
static VINT plutex_nsized;

static uint32_t P_CartGet32(const uint8_t *b)
{
	return ((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) | ((uint32_t)b[2] << 8) | b[3];
}

static uint32_t P_CartGetLE32(const volatile uint8_t *b)
{
	return ((uint32_t)b[3] << 24) | ((uint32_t)b[2] << 16) | ((uint32_t)b[1] << 8) | b[0];
}

static uint32_t P_CartRecord(void)
{
	/* through the cache: the 68000 writes it */
	return *(volatile uint32_t *)(0x22000000 + plutex_recoff);
}

static void P_CartInit(void)
{
	int l;
	if (plutex_ok >= 0)
		return;
	plutex_ok = 0;
	l = W_CheckNumForName("CARTBLK");
	if (l < 0 || !W_IsIWad(l))
		return;
	{
		const uint8_t *b = W_POINTLUMPNUM(l);
		plutex_blkiwad = P_CartGet32(b);
		plutex_blk = ((uintptr_t)I_WadBase() + plutex_blkiwad - 0x02000000) & 0x3FFFFF;
		plutex_blklen = P_CartGet32(b + 4);
	}
	l = W_CheckNumForName("CARTREC");
	if (l < 0 || !W_IsIWad(l))
		return;
	plutex_recoff = ((uintptr_t)W_POINTLUMPNUM(l) - 0x02000000) & 0x3FFFFF;
	plutex_ok = 1;
}

static void P_CartMark(uint32_t v)
{
	volatile uint32_t *buf = (volatile uint32_t *)I_GetCDFileBuffer();
	if (P_CartRecord() == v)
		return;
	buf[0] = v;
	buf[1] = buf[2] = buf[3] = 0;
	Mars_CartWrite(plutex_recoff, 16);
}

/* the block's own bytes back from PLUTONIA.WAD (CARTPOOL) */
static void P_CartRestore(void)
{
	int len, off, n, i;
	uint32_t pos = 0, size = 0;
	const volatile uint8_t *b;

	len = I_OpenCDFileByName("PLUTONIA.WAD", &off);
	if (len <= 0)
		return;
	I_SeekCDFile(0, SEEK_SET);
	if (I_ReadCDFile(12) < 0)
		return;
	b = I_GetCDFileBuffer();
	n = P_CartGetLE32(b + 4);
	i = P_CartGetLE32(b + 8);
	if (n <= 0 || n > 4096)
		return;
	I_SeekCDFile(i, SEEK_SET);
	if (I_ReadCDFile(n * 16) < 0)
		return;
	b = I_GetCDFileBuffer();
	for (i = n - 1; i >= 0; i--) {
		const volatile uint8_t *e = b + i * 16;
		if (e[8] == 'C' && e[9] == 'A' && e[10] == 'R' && e[11] == 'T' && e[12] == 'P' && e[13] == 'O'
			&& e[14] == 'O' && e[15] == 'L') {
			pos = P_CartGetLE32(e);
			size = P_CartGetLE32(e + 4);
			break;
		}
	}
	if (i < 0 || size != plutex_blklen)
		return;
	for (i = 0; i < (int)size; i += 0x8000) {
		int c = size - i < 0x8000 ? size - i : 0x8000;
		I_SeekCDFile(pos + i, SEEK_SET);
		if (I_ReadCDFile(c) < 0)
			return;
		Mars_CartWrite(plutex_blk + i, c);
	}
	P_CartMark(0);
	Mars_ClearCache();
	Mars_CommSlaveClearCache();
}

/* the sizes the last map's pictures gave their donor names, back to the base game's */
static void P_CartUnsize(void)
{
	while (plutex_nsized > 0) {
		plutex_nsized--;
		textures[plutex_sized[plutex_nsized].tex].width = plutex_sized[plutex_nsized].w;
		textures[plutex_sized[plutex_nsized].tex].height = plutex_sized[plutex_nsized].h;
	}
}

/* a picture's own size (its header) for every texture drawn from that lump */
static void P_CartSize(int lumpnum2, const uint8_t *data)
{
	int n, w = (data[0] << 8) | data[1], h = (data[2] << 8) | data[3];
	for (n = 0; n < numtextures; n++) {
		if (textures[n].lumpnum != lumpnum2)
			continue;
		if (textures[n].width == w && textures[n].height == h)
			continue;
		if (plutex_nsized >= MAX_AUX_TEXTURES)
			return;
		plutex_sized[plutex_nsized].tex = n;
		plutex_sized[plutex_nsized].w = textures[n].width;
		plutex_sized[plutex_nsized].h = textures[n].height;
		plutex_nsized++;
		textures[n].width = w;
		textures[n].height = h;
	}
}

/* back to the game select screen (d_main.c): the block back if Plutonia had it, so the RAM cart's loader
   finds the game as it put it there at the next start (a changed cart is copied again: a minute) */
void P_CartLeave(void)
{
	P_CartInit();
	if (plutex_ok > 0 && P_CartRecord() == PLUTEX_DIRTY)
		P_CartRestore();
}

#endif

/*
=================
=
= P_SetupLevel
=
=================
*/
void P_SetupLevel (const char *lumpname, skill_t skill, const char *sky)
{
	int i;
#ifndef MARS
	mobj_t	*mobj;
#endif
	extern VINT	cy;
	VINT lumpnum, lumps[ML_BLOCKMAP+1+MAX_AUX_TEXTURES];
	lumpinfo_t li[ML_BLOCKMAP+1+MAX_AUX_TEXTURES];
	int skytexture;
	boolean havebossspit = false;
	int gamezonemargin;
	jagobj_t *skyheader;
	boolean havesky;
	boolean romlevel = false;

	M_ClearRandom ();

	P_LoadingPlaque ();
	
D_printf ("P_SetupLevel(%s,%i)\n",lumpname,skill);

	P_InitThinkers ();

	R_ClearTextures();
#ifdef CD32X_PLUTEX
	P_CartUnsize();
	P_CartInit();
#endif

	if (!sky || !*sky) {
		sky = "SKY1";
	}

	skyheader = NULL;
	skytexturep = NULL;
	skytexture = -1;
	skycolormaps = NULL;

	W_LoadPWAD(PWAD_CD);
#ifdef CD32X_PLUTEX
	/* another game while the block holds Plutonia's pictures: the block back first */
	if (plutex_ok > 0 && P_CartRecord() == PLUTEX_DIRTY && W_CheckNumForName("CARTPOOL") < 0) {
		P_CartRestore();
		W_LoadPWAD(PWAD_CD);
	}
#endif

	lumpnum = W_CheckNumForName(lumpname);
	if (lumpnum < 0)
		I_Error("Map %s not found!", lumpname);

	/* build a temp in-memory PWAD */
	for (i = 0; i < ML_BLOCKMAP+1+MAX_AUX_TEXTURES; i++)
		lumps[i] = lumpnum+i;

#ifdef CD32X
	if (P_RomMap(lumpnum))
	{
		/* a ROM map: read in place from the IWAD, no in-memory PWAD (its lump list only for the
		   extra lumps after BLOCKMAP; the list ends at the next map's marker or the IWAD's end) */
		for (i = 0; i < ML_BLOCKMAP+1+MAX_AUX_TEXTURES; i++)
			if (!W_IsIWad(lumps[i]))
				lumps[i] = -1;
		W_CacheWADLumps(li, ML_BLOCKMAP+1+MAX_AUX_TEXTURES, lumps, false);
		romlevel = true;
	}
	else
#endif
	{
	W_CacheWADLumps(li, ML_BLOCKMAP+1+MAX_AUX_TEXTURES, lumps, true);

	lumpnum = W_GetNumForName(lumpname);
	}

#ifdef CD32X_PLUTEX
	/* CARTMAP and CARTDATA (the first extra lumps, tools/make_game.py --cart-iwad): CARTDATA is the cart
	   block's picture for this map, written there now (one read from the CD); CARTMAP (big-endian: 'CMAP',
	   count, then per piece: name[8], kind - 1 texture, 2 flat, 3 sky, 4 one of the map's own lumps -, its
	   ML_xxx, its offset in the block, its size) says what is where: the map's read-only lumps are used
	   in place (P_CartLevel), the pictures are set below with the RAM's */
	D_memset(plutex_lvl, 0, sizeof(plutex_lvl));
	plutex_lvlbase = -1;
	plutex_cmap = -1;
	if (plutex_ok > 0 && !romlevel)
	{
		int icm = -1, idata = -1;
		/* this map's own first two extra lumps only: the list holds the next maps' lumps too */
		for (i = 0; i < 2; i++)
		{
			lumpinfo_t *l = &li[ML_BLOCKMAP + 1 + i];
			char name[9];
			D_memcpy(name, l->name, 8);
			name[0] = name[0] & ~0x80;
			name[8] = 0;
			if (i == 0 && l->size && !D_strcasecmp(name, "CARTMAP"))
				icm = i;
			else if (i == 1 && icm == 0 && l->size && !D_strcasecmp(name, "CARTDATA"))
				idata = i;
		}
		if (icm >= 0 && idata >= 0 && (uint32_t)li[ML_BLOCKMAP + 1 + idata].size <= plutex_blklen)
		{
			const volatile uint8_t *cm = W_POINTLUMPNUM(lumpnum + ML_BLOCKMAP + 1 + icm);
			uint32_t lvl[ML_BLOCKMAP + 1];
			int e, cnt = P_CartGet32((const uint8_t *)cm + 4);
			D_memset(lvl, 0, sizeof(lvl));
			if (P_CartGet32((const uint8_t *)cm) == 0x434D4150)	/* 'CMAP' */
			{
				for (e = 0; e < cnt && e < MAX_AUX_TEXTURES; e++)
				{
					const volatile uint8_t *en = cm + 8 + e * 20;
					int kind = (en[8] << 8) | en[9], ml = (en[10] << 8) | en[11];
					uint32_t o = P_CartGet32((const uint8_t *)en + 12);
					if (kind == 4 && ml >= ML_VERTEXES && ml <= ML_BLOCKMAP)
						lvl[ml] = o + 1;
				}
				P_CartMark(PLUTEX_DIRTY);
				W_ReadLumpToCart(lumpnum + ML_BLOCKMAP + 1 + idata, plutex_blk);
				Mars_ClearCache();
				for (e = 0; e <= ML_BLOCKMAP; e++)
					if (lvl[e]) {
						plutex_lvl[e] = (uint8_t *)I_WadBase() + plutex_blkiwad + lvl[e] - 1;
						plutex_lvlbase = lumpnum;
					}
				plutex_cmap = icm;
			}
		}
	}
#endif

#if defined(USE_SMALL_LUMPS) && defined(ENABLE_SSF_MAPPER)
	if (W_IsIWad(lumpnum+ML_SEGS))
	{
		int oldpage = 255;
		I_SetBankPage(oldpage);

		W_POINTLUMPNUM(lumpnum+ML_SEGS);

		segspage = I_GetBankPage();
		if (segspage == oldpage) {
			// not in bank-switched area
			segspage = -1;
		}
	}
	else
	{
		segspage = -1;
	}
#endif

/* note: most of this ordering is important	 */
	P_LoadLineDefs (lumpnum+ML_LINEDEFS);
	P_LoadSideDefs (lumpnum+ML_SIDEDEFS);
	P_LoadVertexes (lumpnum+ML_VERTEXES);
	P_LoadSegs (lumpnum+ML_SEGS);
	P_LoadSubsectors (lumpnum+ML_SSECTORS);
	P_LoadNodes (lumpnum+ML_NODES);
	P_LoadSectors (lumpnum+ML_SECTORS);
	P_LoadRejectMatrix (lumpnum+ML_REJECT);
	P_LoadBlockMap (lumpnum+ML_BLOCKMAP);

	validcount = Z_Malloc((numlines + 1) * sizeof(*validcount), PU_LEVEL);
	D_memset(validcount, 0, (numlines + 1) * sizeof(*validcount));
	validcount[0] = 1; // cpu 0

	// G_DeathMatchSpawnPlayer is going to need this
	I_SetThreadLocalVar(DOOMTLS_VALIDCOUNT, &validcount[0]);

	P_GroupLines ();

	if (!romlevel
#ifdef CD32X_PLUTEX
		&& !P_CartLevel(lumpnum+ML_SEGS)	/* sorted already */
#endif
		)
		P_SortSegs();

	if (netgame == gt_deathmatch)
	{
		itemrespawnque = Z_Malloc(sizeof(*itemrespawnque) * ITEMQUESIZE, PU_LEVEL);
		itemrespawntime = Z_Malloc(sizeof(*itemrespawntime) * ITEMQUESIZE, PU_LEVEL);
		deathmatchstarts = Z_Malloc(sizeof(*deathmatchstarts) * MAXDMSTARTS, PU_LEVEL);
	}
	else
	{
		itemrespawnque = NULL;
		itemrespawntime = NULL;
		deathmatchstarts = NULL;
	}

	havesky = false;
	for (i = 0; i < numsectors; i++) {
		if (*(int8_t *)&sectors[i].ceilingpic == -1) {
			havesky = true;
			break;
		}
	}

	bodyqueslot = 0;
	deathmatch_p = deathmatchstarts;
	P_LoadThings (lumpnum+ML_THINGS, &havebossspit);

	// load custom replacement textures from CD to RAM
	{
		boolean istexture = false;
		boolean isflat = false;
#ifdef CD32X_PLUTEX
		boolean cartwrote = plutex_cmap >= 0;

		/* the pictures in the cart block (CARTMAP, above) */
		if (plutex_cmap >= 0)
		{
			const volatile uint8_t *cm = W_POINTLUMPNUM(lumpnum + ML_BLOCKMAP + 1 + plutex_cmap);
			int e, cnt = P_CartGet32((const uint8_t *)cm + 4);
			for (e = 0; e < cnt && e < MAX_AUX_TEXTURES; e++)
			{
				const volatile uint8_t *en = cm + 8 + e * 20;
				char name[9];
				int j, kind = (en[8] << 8) | en[9];
				uint32_t o = P_CartGet32((const uint8_t *)en + 12), size = P_CartGet32((const uint8_t *)en + 16);
				uint8_t *data = (uint8_t *)I_WadBase() + plutex_blkiwad + o;
				for (j = 0; j < 8; j++)
					name[j] = en[j];
				name[8] = 0;
				if (o + size > plutex_blklen)
					continue;
				if (kind == 1) {
					j = R_CheckTextureNumForName(name);
					if (j >= 0) {
						int n, lumpnum2 = textures[j].lumpnum;
						P_CartSize(lumpnum2, data);
						for (n = 0; n < numtextures; n++)
							if (textures[n].lumpnum == lumpnum2)
								R_SetTextureData(&textures[n], data, size, true);
					}
				} else if (kind == 2) {
					j = R_FlatNumForName(name);
					if (j >= 0)
						R_SetFlatData(j, data, size);
				} else if (kind == 3) {
					if (havesky && !D_strcasecmp(name, sky))
						skytexturep = R_SkipJagObjHeader(data, size, 256, 128, &skyheader);
				}
			}
		}
#endif

		for (i = 0; i < MAX_AUX_TEXTURES; i++)
		{
			int j, k;
			uint8_t *data;
			lumpinfo_t *l;
			char name[9];

			k = ML_BLOCKMAP + 1 + i;
			l = &li[k];
			if (!l->name[0])
				break;

			D_memcpy(name, l->name, 8);
			name[0] = name[0] & ~0x80;
			name[8] = 0;

			if (!l->size)
			{
				if (!istexture && !D_strcasecmp(name, "T_START"))
					istexture = true;
				else if (istexture && !D_strcasecmp(name, "T_END"))
					istexture = false;
				else if (!istexture && !D_strcasecmp(name, "F_START"))
					isflat = true;
				else if (isflat && !D_strcasecmp(name, "F_END"))
					isflat = false;
				else
					break;
				continue;
			}

			// check if it's a texture
			if (istexture) {
				j = R_CheckTextureNumForName (name);
				if (j >= 0)
				{
					int n;
					int lumpnum2 = textures[j].lumpnum;
					if (romlevel)
						data = W_POINTLUMPNUM(lumpnum+k);
					else {
					data = Z_Malloc (l->size, PU_LEVEL);
					W_ReadLump(lumpnum+k, data);
					}
#ifdef CD32X_PLUTEX
					if (plutex_ok > 0 && !romlevel)
						P_CartSize(lumpnum2, data);
#endif
					for (n = 0; n < numtextures; n++)
					{
						if (textures[n].lumpnum == lumpnum2)
							R_SetTextureData(&textures[n], data, l->size, true);
					}
				}
				continue;
			}

			// a flat?
			if (isflat) {
				j = R_FlatNumForName(name);
				if (j >= 0) {
					if (romlevel)
						data = W_POINTLUMPNUM(lumpnum + k);
					else {
					data = Z_Malloc (l->size, PU_LEVEL);
					W_ReadLump(lumpnum + k, data);
					}
					R_SetFlatData(j, data, l->size);
					continue;
				}
			}

			// a sky?
			if (havesky && !D_strcasecmp(name, sky)) {
				if (romlevel)
					data = W_POINTLUMPNUM(lumpnum + k);
				else {
				data = Z_Malloc (l->size, PU_LEVEL);
				W_ReadLump(lumpnum + k, data);
				}
				skytexturep = R_SkipJagObjHeader(data, l->size, 256, 128, &skyheader);
				continue;
			}
		}
#ifdef CD32X_PLUTEX
		if (cartwrote) {
			Mars_ClearCache();
			Mars_CommSlaveClearCache();
		}
#endif
	}

	W_LoadPWAD(PWAD_NONE);

	if (havesky && !skytexturep) {
		skytexture = W_CheckNumForName(sky);
		if (skytexture == -1) {
			sky = "SKY1";
			skytexture = W_CheckNumForName(sky);
		}

		if (skytexture != -1) {
			if (W_IsCompressed(skytexture))
			{
				skytexturep = Z_Malloc (W_LumpLength(skytexture),PU_LEVEL);
				W_ReadLump(skytexture, skytexturep);
			}
			else
				skytexturep = W_POINTLUMPNUM(skytexture);

			skydepth = 3;
			skytexturep = R_SkipJagObjHeader(skytexturep, W_LumpLength(skytexture), 256, 128, &skyheader);
		}
	}

#ifdef CD32X_PLUTEX
	if (skytexturep)
		skydepth = 3;	/* 8-bit unless its header says 4-bit (below), not the last map's */
#endif
	if (skyheader && BIGSHORT(skyheader->depth) == 2) {
		// 4-bit sky has a custom colormap appended at the end of the file
		skydepth = 2;
		skycolormaps = (int8_t *)skytexturep + 64*256;
	}

	R_FixupTextures();

/* */
/* if deathmatch, randomly spawn the active players */
/* */
	if (netgame == gt_deathmatch)
	{
		int i;
		for (i=0 ; i<MAXPLAYERS ; i++)
			if (playeringame[i])
			{	/* must give a player spot before deathmatchspawn */
				mobj_t *mobj = P_SpawnMobj (deathmatchstarts[0].x<<16
				,deathmatchstarts[0].y<<16,0, MT_PLAYER);
				mobj->player = i + 1;
				players[i].mo = mobj;
				G_DeathMatchSpawnPlayer (i);
				P_RemoveMobj (mobj);
				bodyqueslot = 0; // bodyque shouldn't he holding a reference to removed mobj
			}
	}

/* set up world state */
	P_SpawnSpecials ();
	ST_InitEveryLevel ();
	
/*I_Error("free memory: 0x%x\n", Z_FreeMemory(mainzone)); */
/*printf ("free memory: 0x%x\n", Z_FreeMemory(mainzone)); */

	cy = 4;

#ifdef JAGUAR
{
extern byte *debugscreen;
	D_memset (debugscreen,0,32*224);
	
}
#endif

	iquehead = iquetail = 0;
	gamepaused = false;

	gamezonemargin = DEFAULT_GAME_ZONE_MARGIN;
	if (havebossspit)
		gamezonemargin *= 2;
	R_SetupLevel(gamezonemargin);

#ifdef MARS
	Mars_CommSlaveClearCache();
#endif
}


/*
=================
=
= P_Init
=
=================
*/

void P_Init (void)
{
	anims = Z_Malloc(sizeof(*anims) * MAXANIMS, PU_STATIC);
	switchlist = Z_Malloc(sizeof(*switchlist)* MAXSWITCHES * 2, PU_STATIC);
	buttonlist = Z_Malloc(sizeof(*buttonlist) * MAXBUTTONS, PU_STATIC);
	linespeciallist = Z_Malloc(sizeof(*linespeciallist) * MAXLINEANIMS, PU_STATIC);

	activeplats = Z_Malloc(sizeof(*activeplats) * MAXPLATS, PU_STATIC);
	activeceilings = Z_Malloc(sizeof(*activeceilings) * MAXCEILINGS, PU_STATIC);

	P_InitSwitchList ();
	P_InitPicAnims ();
#ifndef MARS
	pausepic = W_CacheLumpName ("PAUSED",PU_STATIC);
#endif
}



